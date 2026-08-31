"""voice/stt.py — mikrofon yakalama + sessizlik algılama (VAD) + faster-whisper.

Eşik 1'in "kulak" yarısı. JARVIS'in konuşulanı duyup metne çevirmesini sağlar.

Tasarım kararı — **donanım mantıktan ayrıldı**: kayıt döngüsü ses parçalarını
(`chunk`) bir `chunk_source`'tan alır. Gerçekte bu `sounddevice`'tir; testte düz
float listeleridir. Böylece sessizlik algılama mantığı mikrofon olmadan,
deterministik olarak test edilebilir. Aynısı transkripsiyon için de geçerli:
testler model indirmez.

`sounddevice`, `faster_whisper` ve `numpy` **modül düzeyinde import edilmez** —
biri ses cihazı açar, diğeri model indirir. Üçü de yalnızca varsayılan
çalıştırıcıların içinde, tembel import edilir. `tests/test_voice_stt.py` bunu
AST ile kilitler.

`config.py` de import edilmez: import anında `load_dotenv()` çağırıp
`HF_*_OFFLINE` yazıyor (CLAUDE.md §9). Varsayılanlar burada tekrarlanır;
`main.py` isterse config değerlerini geçirir.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

__all__ = [
    "DEFAULT_SAMPLE_RATE",
    "DEFAULT_SILENCE_THRESHOLD",
    "DEFAULT_SILENCE_DURATION_S",
    "rms",
    "is_silent",
    "RecordResult",
    "STTResult",
    "MicrophoneRecorder",
    "FasterWhisperTranscriber",
    "VoiceListener",
]

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_MS = 30
DEFAULT_SILENCE_THRESHOLD = 0.01     # config.py SILENCE_THRESHOLD ile aynı
DEFAULT_SILENCE_DURATION_S = 1.5     # config.py SILENCE_DURATION ile aynı
DEFAULT_MAX_DURATION_S = 20.0
DEFAULT_START_TIMEOUT_S = 8.0


# --------------------------------------------------------------------------- #
# Saf VAD mantığı — sayısal kütüphane gerektirmez
# --------------------------------------------------------------------------- #

def rms(chunk: Sequence[float]) -> float:
    """Parçanın karekök-ortalama-kare enerjisi. Boş parça için 0.0."""
    if not len(chunk):
        return 0.0
    toplam = 0.0
    for ornek in chunk:
        toplam += float(ornek) * float(ornek)
    return math.sqrt(toplam / len(chunk))


def is_silent(chunk: Sequence[float], threshold: float) -> bool:
    """Parça sessiz mi? Eşik altındaki enerji sessizlik sayılır."""
    return rms(chunk) < threshold


# --------------------------------------------------------------------------- #
# Sonuç tipleri
# --------------------------------------------------------------------------- #

@dataclass
class RecordResult:
    """Kayıt sonucu. Başarısızlık istisna değil, yapısal sonuçtur."""

    ok: bool
    samples: List[float] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass
class STTResult:
    """Dinleme sonucu.

    duration_ms ölçülmediyse None'dır — asla 0 değil, çünkü 0 yanlış bir
    iddia olurdu (aynı disiplin: scripts/j0_tts_adapters.py TTSResult).
    """

    ok: bool
    text: str = ""
    duration_ms: Optional[float] = None
    warning: Optional[str] = None


# --------------------------------------------------------------------------- #
# Mikrofon kaydı
# --------------------------------------------------------------------------- #

class MicrophoneRecorder:
    """Kullanıcı susana kadar mikrofonu dinler.

    Akış: baştaki sessizlik atlanır → konuşma başlayınca biriktirilir →
    ``silence_duration_s`` kadar sessizlik gelince cümle tamamlanmış sayılır.

    ``start_timeout_s`` içinde hiç konuşma gelmezse boş sonuç döner; sessizlik
    Whisper'a gönderilmez.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        chunk_ms: int = DEFAULT_CHUNK_MS,
        silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
        silence_duration_s: float = DEFAULT_SILENCE_DURATION_S,
        max_duration_s: float = DEFAULT_MAX_DURATION_S,
        start_timeout_s: float = DEFAULT_START_TIMEOUT_S,
        chunk_source: Optional[Callable[[], object]] = None,
        device=None,
    ) -> None:
        if chunk_ms <= 0:
            raise ValueError("chunk_ms pozitif olmalı")
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.chunk_samples = sample_rate * chunk_ms // 1000
        self.silence_threshold = silence_threshold
        self.silence_duration_s = silence_duration_s
        self.max_duration_s = max_duration_s
        self.start_timeout_s = start_timeout_s
        self._chunk_source = chunk_source
        self._device = device

    # Parça sayısına çevrilmiş eşikler — zamanlayıcı yerine sayaç kullanılır ki
    # test gerçek zaman beklemesin ve sonuç deterministik olsun.
    def _chunks_for(self, seconds: float) -> int:
        return max(1, int(round(seconds * 1000.0 / self.chunk_ms)))

    def record(self) -> RecordResult:
        source = self._chunk_source or self._default_chunk_source
        try:
            akis = iter(source())
        except Exception as exc:  # noqa: BLE001 - yüzeye çıkar, yutulmaz
            return RecordResult(ok=False, reason=f"audio_open_error: {exc}")

        sessizlik_siniri = self._chunks_for(self.silence_duration_s)
        baslangic_siniri = self._chunks_for(self.start_timeout_s)
        max_parca = self._chunks_for(self.max_duration_s)

        samples: List[float] = []
        konusma_basladi = False
        ardarda_sessiz = 0
        bekleme = 0

        for parca in akis:
            if not konusma_basladi:
                if is_silent(parca, self.silence_threshold):
                    bekleme += 1
                    if bekleme >= baslangic_siniri:
                        return RecordResult(ok=False, reason="no_speech_detected")
                    continue
                konusma_basladi = True

            samples.extend(float(x) for x in parca)

            if is_silent(parca, self.silence_threshold):
                ardarda_sessiz += 1
                if ardarda_sessiz >= sessizlik_siniri:
                    return RecordResult(ok=True, samples=samples)
            else:
                ardarda_sessiz = 0

            if len(samples) >= max_parca * self.chunk_samples:
                return RecordResult(
                    ok=True, samples=samples, reason="max_duration_reached"
                )

        if not konusma_basladi:
            return RecordResult(ok=False, reason="no_speech_detected")
        return RecordResult(ok=True, samples=samples, reason="source_exhausted")

    def _default_chunk_source(self):
        """Gerçek mikrofon. sounddevice tembel import edilir."""
        import numpy as np
        import sounddevice as sd

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.chunk_samples,
            device=self._device,
        )

        def _uret():
            with stream:
                while True:
                    veri, _tasma = stream.read(self.chunk_samples)
                    yield np.asarray(veri, dtype="float32").reshape(-1).tolist()

        return _uret()


# --------------------------------------------------------------------------- #
# Transkripsiyon
# --------------------------------------------------------------------------- #

class FasterWhisperTranscriber:
    """faster-whisper sarmalayıcısı. Model ilk çağrıda yüklenir, sonra tutulur.

    Yerel çalışır — ses bu makineden çıkmaz. Model ilk kullanımda diske iner.
    """

    def __init__(
        self,
        model_size: str = "small",
        language: str = "tr",
        device: str = "cpu",
        compute_type: str = "int8",
        model_factory: Optional[Callable[[], object]] = None,
    ) -> None:
        self.model_size = model_size
        self.language = language
        #: Varsayılan **cpu**, "auto" değil. Bu makinede RTX 3070 var ama
        #: CTranslate2'nin istediği CUDA kütüphaneleri (cublas64_12.dll) kurulu
        #: değil; "auto" GPU'yu seçip çalışma anında çöküyordu. GPU'ya geçiş
        #: bilinçli bir karar olmalı, sessiz bir varsayılan değil.
        self.device = device
        self.compute_type = compute_type
        self._model_factory = model_factory
        self._model = None
        #: GPU denenip başarısız olduysa burada görünür kalır.
        self.fallback_warning: Optional[str] = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        if self._model_factory is not None:
            self._model = self._model_factory()
            return self._model

        from faster_whisper import WhisperModel

        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:  # noqa: BLE001
            if self.device == "cpu":
                raise
            # GPU yolu kurulamadı (eksik CUDA kütüphanesi vb.). Sessizce
            # çökmek yerine CPU'ya düş ve nedeni görünür bırak.
            self.fallback_warning = (
                f"device={self.device!r} kullanılamadı ({exc}); cpu/int8'e düşüldü"
            )
            self.device = "cpu"
            self.compute_type = "int8"
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
        return self._model

    def __call__(self, samples: Sequence[float], sample_rate: int) -> str:
        import numpy as np

        audio = np.asarray(samples, dtype="float32")
        segments, _info = self._get_model().transcribe(
            audio,
            language=self.language,
            beam_size=1,
            # İKİNCİ SAVUNMA. Whisper sessizlik ve gürültü üzerine metin
            # UYDURUR: 1 saniyelik saf sessizliğe "Bu dizinin betimlemesi,
            # Yeni Gizem..." diye karşılık verdiği ölçüldü. MicrophoneRecorder
            # zaten saf sessizliği göndermiyor; bu, konuşmanın sonundaki
            # sessizlik kuyruğu için ikinci katman.
            vad_filter=True,
        )
        return " ".join(seg.text for seg in segments)


# --------------------------------------------------------------------------- #
# Dinleyici — kayıt + transkripsiyon
# --------------------------------------------------------------------------- #

class VoiceListener:
    """Bir cümle dinler ve metne çevirir.

    Hiçbir hata istisna olarak dışarı sızmaz; hepsi ``STTResult.warning``
    içinde görünür kalır ki çağıran try/except olmadan klavyeye düşebilsin.
    """

    def __init__(
        self,
        recorder: Optional[MicrophoneRecorder] = None,
        transcriber: Optional[Callable[[Sequence[float], int], str]] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        self.sample_rate = sample_rate
        self._recorder = recorder if recorder is not None else MicrophoneRecorder(
            sample_rate=sample_rate
        )
        self._transcriber = transcriber

    def _get_transcriber(self):
        if self._transcriber is None:
            self._transcriber = FasterWhisperTranscriber()
        return self._transcriber

    def listen(self) -> STTResult:
        start = time.perf_counter()

        kayit = self._recorder.record()
        if not kayit.ok or not kayit.samples:
            return STTResult(
                ok=False,
                warning=f"stt_no_input: {kayit.reason or 'unknown'}",
            )

        try:
            ham = self._get_transcriber()(kayit.samples, self.sample_rate)
        except Exception as exc:  # noqa: BLE001 - yüzeye çıkar, yutulmaz
            return STTResult(ok=False, warning=f"transcription_error: {exc}")

        metin = (ham or "").strip()
        if not metin:
            return STTResult(
                ok=False,
                warning="empty_transcription: ses alındı ama metin çıkmadı",
            )

        return STTResult(
            ok=True,
            text=metin,
            duration_ms=(time.perf_counter() - start) * 1000.0,
        )
