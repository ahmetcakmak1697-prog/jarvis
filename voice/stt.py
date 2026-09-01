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
    "resolve_mic_device",
    "select_input_device",
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

#: Hangi mikrofonun dinleneceğini seçer. Boş bırakılırsa işletim sisteminin
#: varsayılan giriş aygıtı kullanılır — makinede birden fazla mikrofon varsa
#: bu, konuşulan aygıt olmayabilir ve JARVIS sessizlik duyar.
MIC_DEVICE_ENV = "JARVIS_MIC_DEVICE"


def resolve_mic_device():
    """``JARVIS_MIC_DEVICE`` değerini sounddevice'in beklediği tipe çevirir.

    Tam sayı verilirse aygıt indeksi, aksi halde isim parçası olarak geçer
    (sounddevice alt-dize eşleşmesi yapar). İsim tercih edilir: indeksler
    aygıt yeniden bağlandığında kayar, isim kaymaz.

    Boş/tanımsız değer ``None`` döner — yani mevcut davranış korunur.
    Ortam **çağrı anında** okunur; ``.env`` bu modül import edildikten sonra
    yüklenebiliyor.
    """
    import os

    ham = (os.getenv(MIC_DEVICE_ENV) or "").strip()
    if not ham:
        return None
    return int(ham) if ham.isdigit() else ham


def select_input_device(spec, query=None, check=None):
    """Bir aygıt belirtimini (``None``/indeks/isim) somut indekse çevirir.

    Neden ayrı bir katman: ``resolve_mic_device()`` yalnız ortamı *ayrıştırır*
    ve saf kalır (sounddevice'a dokunmaz). Aygıt *seçimi* donanım bilgisi
    ister, o yüzden akış açılırken burada yapılır.

    Ölçüldü: bu makinede ``check_input_settings("SoloCast")`` →
    *"Multiple input devices found"*, çünkü isim dört host API'de birden
    eşleşiyor ve sounddevice ilk eşleşmeye düşmüyor, reddediyor. Bu yüzden
    ismi kendimiz çözüyoruz: eşleşen **giriş** aygıtları arasından
    gerçekten **açılabilen** ilkini seçiyoruz.

    Açık indeks doğrulanmadan geçer — o kullanıcının kararıdır.
    Eşleşme bulunamazsa ``None`` döner: işletim sistemi varsayılanına
    düşmek, yanlış aygıtı zorlamaktan iyidir.
    """
    if spec is None or isinstance(spec, int):
        return spec

    if query is None or check is None:
        import sounddevice as sd

        if query is None:
            def query():
                return sd.query_devices()

        if check is None:
            def check(index):
                try:
                    sd.check_input_settings(
                        device=index, channels=1,
                        samplerate=DEFAULT_SAMPLE_RATE, dtype="float32",
                    )
                    return True
                except Exception:  # noqa: BLE001
                    return False

    from agents.data_classifier import _fold_tr

    aranan = _fold_tr(str(spec))
    for indeks, aygit in enumerate(query()):
        if aygit.get("max_input_channels", 0) < 1:
            continue  # çıkış aygıtı asla mikrofon olarak seçilmez
        if aranan not in _fold_tr(aygit.get("name", "")):
            continue
        if check(indeks):
            return indeks
    return None


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
    """Kayıt sonucu. Başarısızlık istisna değil, yapısal sonuçtur.

    ``diagnostic`` **ek** bir alandır; ``reason`` sözleşmesini değiştirmez.
    Ölü akış gibi, kullanıcının kendi başına asla çözemeyeceği durumlarda
    doldurulur — "no_speech_detected" doğrudur ama nedeni anlatmaz.
    """

    ok: bool
    samples: List[float] = field(default_factory=list)
    reason: Optional[str] = None
    diagnostic: Optional[str] = None


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
        # Açık parametre ortamı ezer; verilmezse JARVIS_MIC_DEVICE, o da yoksa
        # işletim sistemi varsayılanı (None).
        self._device = device if device is not None else resolve_mic_device()

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
        # Gerçek bir mikrofon sessiz odada bile TAM sıfır üretmez; gürültü
        # tabanı vardır. Hiç sıfır-dışı örnek görmediysek akış ölüdür
        # (yanlış host API ya da susturulmuş aygıt), sadece sessiz değil.
        sifir_disi_goruldu = False

        for parca in akis:
            if not sifir_disi_goruldu and any(parca):
                sifir_disi_goruldu = True

            if not konusma_basladi:
                if is_silent(parca, self.silence_threshold):
                    bekleme += 1
                    if bekleme >= baslangic_siniri:
                        return RecordResult(
                            ok=False,
                            reason="no_speech_detected",
                            diagnostic=self._olu_akis_tanisi(sifir_disi_goruldu),
                        )
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
            return RecordResult(
                ok=False,
                reason="no_speech_detected",
                diagnostic=self._olu_akis_tanisi(sifir_disi_goruldu),
            )
        return RecordResult(ok=True, samples=samples, reason="source_exhausted")

    def _olu_akis_tanisi(self, sifir_disi_goruldu: bool) -> Optional[str]:
        """Hiç sinyal gelmediyse ne yapılacağını söyleyen tanı metni."""
        if sifir_disi_goruldu:
            return None
        aygit = self._device if self._device is not None else "(varsayılan)"
        return (
            f"dead_audio_stream: aygıt {aygit} yalnız sıfır üretti — hiç sinyal "
            f"yok. Muhtemel neden: yanlış aygıt ya da susturulmuş mikrofon. "
            f"Başka aygıt denemek için {MIC_DEVICE_ENV} değerini değiştirin; "
            f"çalışan aygıtları listelemek için: "
            f"python scripts/j0_mic_check.py --scan"
        )

    def _default_chunk_source(self):
        """Gerçek mikrofon. sounddevice tembel import edilir.

        **Geri-çağırma kullanılır, bloklayan ``read()`` değil.** Ölçüldü
        (2026-09-01, bu makine): DirectSound aygıtında ``InputStream.read()``
        hata vermeden 9600 örneğin 9600'ünü tam sıfır döndürüyor; aynı
        aygıtta geri-çağırma rms 0.020 veriyor. ``sd.rec`` de geri-çağırma
        kullandığı için çalışıyordu. Bloklayan yol bazı host API'lerinde
        sessizce ölü.
        """
        import queue

        import numpy as np
        import sounddevice as sd

        device = select_input_device(self._device)
        kuyruk: "queue.Queue[list]" = queue.Queue()

        def _geri_cagirma(indata, frames, time_info, status):
            # status yutulmaz ama akışı da durdurmaz; taşma bilgisi
            # tanı için anlamlı, kaydı kesmek için değil.
            kuyruk.put(np.asarray(indata, dtype="float32").reshape(-1).tolist())

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.chunk_samples,
            device=device,
            callback=_geri_cagirma,
        )

        # Kuyruk beklemesi için üst sınır: aygıt hiç veri vermezse sonsuza
        # kadar asılı kalınmaz.
        bekleme_s = max(2.0, (self.chunk_ms / 1000.0) * 20)

        def _uret():
            with stream:
                while True:
                    try:
                        yield kuyruk.get(timeout=bekleme_s)
                    except queue.Empty:
                        return

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
            uyari = f"stt_no_input: {kayit.reason or 'unknown'}"
            # Tanı varsa onu da geçir: "no_speech_detected" doğrudur ama
            # ölü akışta kullanıcıya hiçbir şey anlatmaz.
            tani = getattr(kayit, "diagnostic", None)
            if tani:
                uyari = f"{uyari} | {tani}"
            return STTResult(ok=False, warning=uyari)

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
