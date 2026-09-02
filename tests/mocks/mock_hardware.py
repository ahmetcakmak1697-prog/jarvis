"""Donanim dijital ikizi — J2/J5 uydu donanimi icin hafif async mock'lar.

Amac: gercek donanim (INMP441 I2S mikrofon, LD2410C mmWave radar, Home
Assistant WebSocket) olmadan da ses hatti ve varlik-algilama mantigini
deterministik olarak test edebilmek.

Tasarim kurallari:

* **Bagimliliksiz.** Yalniz standart kutuphane. numpy/sounddevice yok.
* **Deterministik.** Gurultu tohumlanmis (`seed`) bir RNG'den gelir; ayni
  seed ayni byte'lari uretir. Test flake'lenmez.
* **Kapanis gozlemlenebilir.** Her mock `closed` bayragi ve sayaclar tutar;
  boylece "kapatilmamis I2S/socket tamponu" testi yazilabilir
  (bkz. ``CODEX_AUDIT_PROTOCOL.md`` §1).
* **Sadeligi koru.** Buraya yalnizca bir testin *bugun* ihtiyac duydugu
  davranis eklenir (``CLAUDE.md`` §2).

Radar cerceve formati hakkinda durustluk notu: ``RadarReading.packet()``
gercek LD2410 basligini/kuyrugunu ve alan sirasini korur ama byte-birebir
degildir; cerceve ayristirmasinin *sekli* test edilebilsin diye vardir,
gercek firmware'in yerine gecmez.
"""

from __future__ import annotations

import asyncio
import math
import random
import struct
from dataclasses import dataclass
from typing import AsyncIterator, Iterable, Sequence

__all__ = [
    "SAMPLE_RATE_HZ",
    "SAMPLE_WIDTH_BYTES",
    "FRAME_MS",
    "FRAME_SAMPLES",
    "MockINMP441Microphone",
    "RadarReading",
    "MockLD2410CRadar",
    "TARGET_NONE",
    "TARGET_MOVING",
    "TARGET_STATIONARY",
    "TARGET_BOTH",
    "DEFAULT_PRESENCE_SCRIPT",
    "MockHomeAssistantWebSocket",
    "HAConnectionDropped",
]


# --------------------------------------------------------------------------
# 1) INMP441 — 16 kHz mono int16 PCM I2S mikrofon
# --------------------------------------------------------------------------

SAMPLE_RATE_HZ = 16_000
SAMPLE_WIDTH_BYTES = 2  # int16, little-endian
FRAME_MS = 20
FRAME_SAMPLES = SAMPLE_RATE_HZ * FRAME_MS // 1000  # 320 ornek / 640 byte


class MockINMP441Microphone:
    """16 kHz mono int16 PCM cercevesi ureten sahte I2S mikrofon.

    ``amplitude=0.0`` (varsayilan) sessizlik uretir — VAD/wake-word'un
    *tetiklenmemesi* gereken durum. ``tone_hz`` verilirse sinus tonu
    uretir; ``noise`` tabana tohumlanmis beyaz gurultu ekler.

    Kullanim::

        async with MockINMP441Microphone(tone_hz=440, amplitude=0.5) as mic:
            async for frame in mic.frames(50):  # 1 saniye
                ...
    """

    def __init__(
        self,
        *,
        frame_ms: int = FRAME_MS,
        amplitude: float = 0.0,
        tone_hz: float | None = None,
        noise: float = 0.0,
        seed: int = 0,
    ) -> None:
        if frame_ms <= 0:
            raise ValueError("frame_ms pozitif olmali")
        if not 0.0 <= amplitude <= 1.0:
            raise ValueError("amplitude 0.0-1.0 araliginda olmali")
        self.sample_rate = SAMPLE_RATE_HZ
        self.frame_ms = frame_ms
        self.frame_samples = SAMPLE_RATE_HZ * frame_ms // 1000
        self.frame_bytes = self.frame_samples * SAMPLE_WIDTH_BYTES
        self._amplitude = amplitude
        self._tone_hz = tone_hz
        self._noise = noise
        self._rng = random.Random(seed)
        self._cursor = 0
        self._closed = False
        self.frames_read = 0
        self.bytes_read = 0

    @property
    def closed(self) -> bool:
        return self._closed

    def _sample(self, n: int) -> int:
        value = 0.0
        if self._tone_hz:
            value += math.sin(2.0 * math.pi * self._tone_hz * n / self.sample_rate)
        if self._noise:
            value += self._rng.uniform(-self._noise, self._noise)
        value *= self._amplitude
        clipped = max(-1.0, min(1.0, value))
        return int(clipped * 32767)

    def read_frame(self) -> bytes:
        """Tek bir PCM cercevesi dondurur (senkron yardimci)."""
        if self._closed:
            raise RuntimeError("mikrofon kapali — kapandiktan sonra okuma yok")
        samples = [self._sample(self._cursor + i) for i in range(self.frame_samples)]
        self._cursor += self.frame_samples
        self.frames_read += 1
        self.bytes_read += self.frame_bytes
        return struct.pack("<%dh" % self.frame_samples, *samples)

    async def frames(self, count: int) -> AsyncIterator[bytes]:
        """``count`` adet PCM cercevesi akitir."""
        for _ in range(count):
            await asyncio.sleep(0)  # kooperatif devir — event loop'u bloke etme
            yield self.read_frame()

    def close(self) -> None:
        self._closed = True

    async def __aenter__(self) -> "MockINMP441Microphone":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.close()


# --------------------------------------------------------------------------
# 2) LD2410C — mmWave varlik / mesafe radari
# --------------------------------------------------------------------------

LD2410_HEADER = b"\xf4\xf3\xf2\xf1"
LD2410_TAIL = b"\xf8\xf7\xf6\xf5"

TARGET_NONE = 0x00
TARGET_MOVING = 0x01
TARGET_STATIONARY = 0x02
TARGET_BOTH = 0x03


@dataclass(frozen=True)
class RadarReading:
    """Tek bir LD2410C hedef raporu."""

    target_state: int = TARGET_NONE
    moving_distance_cm: int = 0
    moving_energy: int = 0
    static_distance_cm: int = 0
    static_energy: int = 0
    detection_distance_cm: int = 0

    @property
    def presence(self) -> bool:
        """Odada biri var mi?"""
        return self.target_state != TARGET_NONE

    def packet(self) -> bytes:
        """Basitlestirilmis LD2410 hedef-veri cercevesi (bkz. modul notu)."""
        body = struct.pack(
            "<BBBHBHBHBB",
            0x02,  # data type: target data
            0xAA,  # head
            self.target_state,
            self.moving_distance_cm,
            self.moving_energy,
            self.static_distance_cm,
            self.static_energy,
            self.detection_distance_cm,
            0x55,  # tail
            0x00,  # check
        )
        return LD2410_HEADER + struct.pack("<H", len(body)) + body + LD2410_TAIL


#: Bos oda -> yaklasan hareket -> sabit oturma -> ayrilis.
DEFAULT_PRESENCE_SCRIPT: tuple[RadarReading, ...] = (
    RadarReading(),
    RadarReading(TARGET_MOVING, 420, 45, 0, 0, 420),
    RadarReading(TARGET_MOVING, 260, 62, 0, 0, 260),
    RadarReading(TARGET_BOTH, 180, 58, 175, 40, 180),
    RadarReading(TARGET_STATIONARY, 0, 0, 172, 44, 172),
    RadarReading(TARGET_STATIONARY, 0, 0, 170, 41, 170),
    RadarReading(TARGET_MOVING, 300, 51, 0, 0, 300),
    RadarReading(),
)


class MockLD2410CRadar:
    """Senaryo-guduml sahte LD2410C radar.

    Varsayilan senaryo :data:`DEFAULT_PRESENCE_SCRIPT`; testler kendi
    okuma dizilerini verebilir. ``loop=True`` senaryoyu bastan sarar.
    """

    def __init__(
        self,
        script: Sequence[RadarReading] | None = None,
        *,
        loop: bool = False,
    ) -> None:
        self._script: list[RadarReading] = list(
            DEFAULT_PRESENCE_SCRIPT if script is None else script
        )
        if not self._script:
            raise ValueError("radar senaryosu bos olamaz")
        self._loop = loop
        self._index = 0
        self._closed = False
        self.reads = 0

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def exhausted(self) -> bool:
        return not self._loop and self._index >= len(self._script)

    def read(self) -> RadarReading:
        """Siradaki okumayi dondurur (senkron yardimci)."""
        if self._closed:
            raise RuntimeError("radar kapali — kapandiktan sonra okuma yok")
        if self.exhausted:
            raise StopIteration("radar senaryosu tuketildi")
        reading = self._script[self._index % len(self._script)]
        self._index += 1
        self.reads += 1
        return reading

    async def readings(self, count: int | None = None) -> AsyncIterator[RadarReading]:
        """Radar okumalarini akitir; ``count`` yoksa senaryo bitene kadar."""
        emitted = 0
        while count is None or emitted < count:
            if self.exhausted:
                return
            await asyncio.sleep(0)
            yield self.read()
            emitted += 1

    async def packets(self, count: int | None = None) -> AsyncIterator[bytes]:
        """Ayni akisi ham cerceve byte'lari olarak verir."""
        async for reading in self.readings(count):
            yield reading.packet()

    def close(self) -> None:
        self._closed = True

    async def __aenter__(self) -> "MockLD2410CRadar":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.close()


# --------------------------------------------------------------------------
# 3) Home Assistant WebSocket — bagli / gecici kopma
# --------------------------------------------------------------------------


class HAConnectionDropped(ConnectionError):
    """Gecici WebSocket kopmasi. Yeniden ``connect()`` ile toparlanabilir."""


class MockHomeAssistantWebSocket:
    """Home Assistant WebSocket baglantisinin sahte durumu.

    Gecici kopmayi ``drop_after`` ile kurgula: o kadar basarili
    gonderimden sonra bir sonraki islem :class:`HAConnectionDropped`
    firlatir ve durum ``disconnected`` olur. ``connect()`` cagrilirsa
    baglanti geri gelir — kopmanin *gecici* olmasi budur.

    Kullanim::

        ws = MockHomeAssistantWebSocket(drop_after=2)
        await ws.connect()
        await ws.send_json({"type": "ping"})
    """

    def __init__(
        self,
        *,
        url: str = "ws://homeassistant.local:8123/api/websocket",
        drop_after: int | None = None,
        max_drops: int = 1,
        inbox: Iterable[dict] | None = None,
    ) -> None:
        self.url = url
        self._drop_after = drop_after
        self._max_drops = max_drops
        self._inbox: list[dict] = list(inbox or ())
        self.state = "disconnected"
        self.sent: list[dict] = []
        self.connect_count = 0
        self.drops_emitted = 0
        self._sends_since_connect = 0
        self._closed = False

    @property
    def connected(self) -> bool:
        return self.state == "connected"

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("WebSocket kapali — kapandiktan sonra kullanim yok")
        if not self.connected:
            raise HAConnectionDropped("WebSocket bagli degil")

    def _maybe_drop(self) -> None:
        if self._drop_after is None or self.drops_emitted >= self._max_drops:
            return
        if self._sends_since_connect >= self._drop_after:
            self.state = "disconnected"
            self.drops_emitted += 1
            raise HAConnectionDropped(
                f"HA baglantisi koptu ({self._sends_since_connect} gonderimden sonra)"
            )

    async def connect(self) -> "MockHomeAssistantWebSocket":
        if self._closed:
            raise RuntimeError("kapali WebSocket yeniden baglanamaz")
        await asyncio.sleep(0)
        self.state = "connected"
        self.connect_count += 1
        self._sends_since_connect = 0
        return self

    async def send_json(self, message: dict) -> None:
        self._require_open()
        self._maybe_drop()
        await asyncio.sleep(0)
        self.sent.append(message)
        self._sends_since_connect += 1

    async def receive_json(self) -> dict:
        self._require_open()
        self._maybe_drop()
        await asyncio.sleep(0)
        if not self._inbox:
            raise HAConnectionDropped("gelen kutusu bos — sunucu sustu")
        return self._inbox.pop(0)

    def queue(self, *messages: dict) -> None:
        """Testin ``receive_json`` ile alacagi mesajlari kuyruga koyar."""
        self._inbox.extend(messages)

    async def close(self) -> None:
        await asyncio.sleep(0)
        self.state = "disconnected"
        self._closed = True

    async def __aenter__(self) -> "MockHomeAssistantWebSocket":
        return await self.connect()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
