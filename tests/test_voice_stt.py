"""voice/stt.py sozlesmesi — mikrofon yakalama + VAD + faster-whisper.

Tasarim karari: kayit dongusu ile ses donanimi AYRILDI. `MicrophoneRecorder`
parcalari (chunk) bir `chunk_source`'tan alir; gercekte bu sounddevice'tir,
testte duz float listeleridir. Boylece sessizlik algilama mantigi mikrofon
olmadan, deterministik olarak test edilir.

Ayni sekilde transkripsiyon da enjekte edilebilir: testler model indirmez.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

SR = 16000
CHUNK_MS = 30
CHUNK = SR * CHUNK_MS // 1000  # 480 ornek


def sessiz(n=1):
    """n adet sessiz parca."""
    return [[0.0] * CHUNK for _ in range(n)]


def konusma(n=1, seviye=0.4):
    """n adet konusma seviyesinde parca (kare dalga -> RMS = seviye)."""
    return [[seviye if i % 2 else -seviye for i in range(CHUNK)] for _ in range(n)]


def kaynak(*gruplar):
    """Parca gruplarini tek bir chunk_source'a cevirir."""
    parcalar = [p for grup in gruplar for p in grup]

    def _source():
        return iter(parcalar)

    return _source


# --------------------------------------------------------------------------- #
# 1. Saf VAD mantigi
# --------------------------------------------------------------------------- #

def test_rms_of_silence_is_zero():
    from voice.stt import rms

    assert rms([0.0] * 100) == 0.0


def test_rms_of_speech_is_above_threshold():
    from voice.stt import rms

    assert rms(konusma(1)[0]) == pytest.approx(0.4, abs=1e-6)


def test_is_silent_uses_threshold():
    from voice.stt import is_silent

    assert is_silent([0.0] * 100, threshold=0.01) is True
    assert is_silent(konusma(1)[0], threshold=0.01) is False


def test_rms_of_empty_chunk_is_zero():
    from voice.stt import rms

    assert rms([]) == 0.0


# --------------------------------------------------------------------------- #
# 2. Kayit dongusu — sessizlik algilama
# --------------------------------------------------------------------------- #

def test_recorder_stops_after_silence_following_speech():
    """Kullanici susunca cumle tamamlanir ve kayit biter."""
    from voice.stt import MicrophoneRecorder

    # 10 parca konusma + 50 parca sessizlik (1.5s @ 30ms) + fazlasi
    rec = MicrophoneRecorder(
        sample_rate=SR, chunk_ms=CHUNK_MS, silence_threshold=0.01,
        silence_duration_s=1.5, max_duration_s=30.0,
        chunk_source=kaynak(konusma(10), sessiz(80)),
    )
    result = rec.record()
    assert result.ok is True
    assert result.reason is None
    # 10 konusma + 50 sessizlik parcasi kadar ornek alinmis olmali
    beklenen = (10 + 50) * CHUNK
    assert len(result.samples) == beklenen


def test_recorder_ignores_leading_silence():
    """Bas taraftaki sessizlik cumleye dahil edilmez."""
    from voice.stt import MicrophoneRecorder

    rec = MicrophoneRecorder(
        sample_rate=SR, chunk_ms=CHUNK_MS, silence_threshold=0.01,
        silence_duration_s=1.5, max_duration_s=30.0, start_timeout_s=10.0,
        chunk_source=kaynak(sessiz(30), konusma(5), sessiz(60)),
    )
    result = rec.record()
    assert result.ok is True
    assert len(result.samples) == (5 + 50) * CHUNK


def test_recorder_gives_up_when_nobody_speaks():
    """Kimse konusmazsa: bos sonuc + gerekce. Whisper'a sessizlik gonderilmez."""
    from voice.stt import MicrophoneRecorder

    rec = MicrophoneRecorder(
        sample_rate=SR, chunk_ms=CHUNK_MS, silence_threshold=0.01,
        silence_duration_s=1.5, max_duration_s=30.0, start_timeout_s=0.6,
        chunk_source=kaynak(sessiz(200)),
    )
    result = rec.record()
    assert result.ok is False
    assert result.reason == "no_speech_detected"
    assert result.samples == []


def test_recorder_respects_max_duration():
    """Susmayan konusma sonsuza kadar kaydedilmez."""
    from voice.stt import MicrophoneRecorder

    rec = MicrophoneRecorder(
        sample_rate=SR, chunk_ms=CHUNK_MS, silence_threshold=0.01,
        silence_duration_s=1.5, max_duration_s=0.9,  # 30 parca
        chunk_source=kaynak(konusma(500)),
    )
    result = rec.record()
    assert result.ok is True
    assert result.reason == "max_duration_reached"
    assert len(result.samples) == 30 * CHUNK


def test_recorder_handles_exhausted_source():
    """Kaynak biterse cokmez."""
    from voice.stt import MicrophoneRecorder

    rec = MicrophoneRecorder(
        sample_rate=SR, chunk_ms=CHUNK_MS,
        chunk_source=kaynak(konusma(3)),
    )
    result = rec.record()
    assert result.ok is True
    assert len(result.samples) == 3 * CHUNK


# --------------------------------------------------------------------------- #
# 3. VoiceListener — kayit + transkripsiyon
# --------------------------------------------------------------------------- #

class FakeRecorder:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def record(self):
        self.calls += 1
        return self._result


def test_listener_transcribes_recorded_audio():
    from voice.stt import RecordResult, VoiceListener

    gorulen = {}

    def fake_transcribe(samples, sample_rate):
        gorulen["n"] = len(samples)
        gorulen["sr"] = sample_rate
        return "  Merhaba efendim  "

    listener = VoiceListener(
        recorder=FakeRecorder(RecordResult(ok=True, samples=[0.1] * 1600)),
        transcriber=fake_transcribe,
        sample_rate=SR,
    )
    result = listener.listen()
    assert result.ok is True
    assert result.text == "Merhaba efendim"  # kirpilmis
    assert gorulen["n"] == 1600
    assert gorulen["sr"] == SR


def test_listener_does_not_transcribe_when_no_speech():
    """Sessizlik Whisper'a gonderilmez -- bosuna CPU/GPU yakilmaz."""
    from voice.stt import RecordResult, VoiceListener

    def exploding(samples, sample_rate):
        raise AssertionError("sessizlik icin transkripsiyon cagrilmamali")

    listener = VoiceListener(
        recorder=FakeRecorder(
            RecordResult(ok=False, samples=[], reason="no_speech_detected")
        ),
        transcriber=exploding,
    )
    result = listener.listen()
    assert result.ok is False
    assert result.text == ""
    assert "no_speech_detected" in (result.warning or "")


def test_listener_surfaces_transcription_failure():
    from voice.stt import RecordResult, VoiceListener

    def broken(samples, sample_rate):
        raise RuntimeError("model yuklenemedi")

    listener = VoiceListener(
        recorder=FakeRecorder(RecordResult(ok=True, samples=[0.1] * 100)),
        transcriber=broken,
    )
    result = listener.listen()
    assert result.ok is False
    assert "transcription_error" in (result.warning or "")
    assert "model yuklenemedi" in (result.warning or "")


def test_listener_rejects_empty_transcription():
    """Whisper bos string donerse bunu gecerli girdi sayma."""
    from voice.stt import RecordResult, VoiceListener

    listener = VoiceListener(
        recorder=FakeRecorder(RecordResult(ok=True, samples=[0.1] * 100)),
        transcriber=lambda s, sr: "   ",
    )
    result = listener.listen()
    assert result.ok is False
    assert "empty_transcription" in (result.warning or "")


# --------------------------------------------------------------------------- #
# 3b. Transcriber cihaz secimi
# --------------------------------------------------------------------------- #

def test_transcriber_defaults_to_cpu():
    """Varsayilan 'auto' DEGIL 'cpu'.

    Bu makinede RTX 3070 var ama CTranslate2'nin istedigi CUDA kutuphaneleri
    (cublas64_12.dll) yok; 'auto' GPU'yu secip calisma aninda cokuyordu.
    """
    from voice.stt import FasterWhisperTranscriber

    assert FasterWhisperTranscriber().device == "cpu"


def test_transcriber_falls_back_to_cpu_when_gpu_unavailable(monkeypatch):
    """GPU kurulamazsa sessizce cokme; cpu'ya dus ve nedeni gorunur birak."""
    import voice.stt as stt_mod

    denenen = []

    class SahteModel:
        def __init__(self, size, device=None, compute_type=None):
            denenen.append(device)
            if device == "cuda":
                raise RuntimeError("cublas64_12.dll bulunamadi")

    sahte_modul = type("m", (), {"WhisperModel": SahteModel})
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", sahte_modul)

    tr = stt_mod.FasterWhisperTranscriber(device="cuda")
    tr._get_model()

    assert denenen == ["cuda", "cpu"]
    assert tr.device == "cpu"
    assert tr.compute_type == "int8"
    assert "cublas" in (tr.fallback_warning or "")


def test_transcriber_enables_whisper_vad_filter():
    """Whisper'in kendi VAD'i ACIK olmali.

    Olculdu: vad_filter=False iken 1 saniyelik SAF SESSIZLIK,
    "Bu dizinin betimlemesi, Yeni Gizem..." diye uydurulmus Turkce metne
    donusuyordu. MicrophoneRecorder zaten saf sessizligi gondermiyor; bu
    ikinci savunma katmani.
    """
    from voice.stt import FasterWhisperTranscriber

    gorulen = {}

    class SahteModel:
        def transcribe(self, audio, **kw):
            gorulen.update(kw)
            return ([], None)

    tr = FasterWhisperTranscriber(model_factory=lambda: SahteModel())
    tr([0.0] * 100, 16000)

    assert gorulen.get("vad_filter") is True
    assert gorulen.get("language") == "tr"


def test_transcriber_cpu_failure_is_not_swallowed(monkeypatch):
    """CPU de kurulamazsa hata yutulmaz -- yukari cikar."""
    import voice.stt as stt_mod

    class PatlayanModel:
        def __init__(self, size, device=None, compute_type=None):
            raise RuntimeError("model dosyasi bozuk")

    sahte_modul = type("m", (), {"WhisperModel": PatlayanModel})
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", sahte_modul)

    with pytest.raises(RuntimeError, match="model dosyasi bozuk"):
        stt_mod.FasterWhisperTranscriber(device="cpu")._get_model()


# --------------------------------------------------------------------------- #
# 4. Import guvenligi
# --------------------------------------------------------------------------- #

def test_import_does_not_pull_audio_or_model_libraries():
    """voice/stt.py import etmek ses cihazina dokunmamali, model yuklememeli.

    sounddevice ve faster_whisper AGIR: biri cihaz acar, digeri model indirir.
    Ikisi de yalnizca varsayilan calistiricilarin ICINDE, tembel import edilir.
    """
    tree = ast.parse((_REPO / "voice" / "stt.py").read_text(encoding="utf-8"))

    ust_seviye = set()
    for node in tree.body:  # yalnizca modul govdesi
        if isinstance(node, ast.Import):
            ust_seviye.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            ust_seviye.add(node.module.split(".")[0])

    for agir in ("sounddevice", "faster_whisper", "numpy", "config"):
        assert agir not in ust_seviye, (
            f"{agir} modul duzeyinde import edilmis; tembel olmali"
        )


def test_import_is_cheap_at_runtime():
    import sys

    for agir in ("sounddevice", "faster_whisper"):
        sys.modules.pop(agir, None)
    import voice.stt  # noqa: F401

    assert "sounddevice" not in sys.modules
    assert "faster_whisper" not in sys.modules
