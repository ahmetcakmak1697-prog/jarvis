"""Ses yakalama yolu — olu akis tespiti ve aygit secimi.

Olculen gercek (2026-09-01, bu makine):

    aygit 1 (MME)          InputStream+read()  rms=0.028  -> CANLI
    aygit 7 (DirectSound)  InputStream+read()  rms=0.000  -> OLU (9600/9600 sifir)
    aygit 7 (DirectSound)  InputStream+callback rms=0.020 -> CANLI

Yani `sd.InputStream` + bloklayan `read()` bazi host API'lerinde hata
VERMEDEN sonsuza kadar sifir dondurur. `sd.rec`'in kullandigi geri-cagirma
mekanizmasi ayni aygitta calisiyor.

Bu iki sonucu doguruyor:
  1. Varsayilan yakalama yolu geri-cagirma olmali.
  2. Yine de olu akis olabilir (susturulmus mikrofon); kullanici
     "no_speech_detected" degil, NE OLDUGUNU gormeli.

Tani ek bir alanda tasinir (`RecordResult.diagnostic`); `reason` sozlesmesi
degismez, boylece mevcut testler aynen gecerli kalir.
"""
from __future__ import annotations

import pytest

CHUNK = 480


def sifir(n):
    """Dijital olu sessizlik — her ornek TAM sifir."""
    return [[0.0] * CHUNK for _ in range(n)]


def gurultu(n, seviye=1e-5):
    """Gercek mikrofonun sessiz odadaki tabani — sifir DEGIL."""
    return [[seviye if i % 3 else -seviye for i in range(CHUNK)] for _ in range(n)]


def konusma(n, seviye=0.4):
    return [[seviye if i % 2 else -seviye for i in range(CHUNK)] for _ in range(n)]


def kaynak(*gruplar):
    parcalar = [p for g in gruplar for p in g]
    return lambda: iter(parcalar)


def kaydedici(src, **kw):
    from voice.stt import MicrophoneRecorder

    varsayilan = dict(sample_rate=16000, chunk_ms=30, silence_threshold=0.01,
                      silence_duration_s=1.5, max_duration_s=30.0,
                      start_timeout_s=0.6, chunk_source=src)
    varsayilan.update(kw)
    return MicrophoneRecorder(**varsayilan)


# --------------------------------------------------------------------------- #
# 1. Olu akis tespiti — EK alan, mevcut sozlesme korunur
# --------------------------------------------------------------------------- #

def test_all_zero_stream_is_flagged_as_dead():
    sonuc = kaydedici(kaynak(sifir(200)), device=7).record()
    assert sonuc.ok is False
    # Mevcut sozlesme AYNEN korunuyor:
    assert sonuc.reason == "no_speech_detected"
    # Yeni bilgi ek alanda:
    assert sonuc.diagnostic is not None
    assert "dead_audio_stream" in sonuc.diagnostic
    assert "7" in sonuc.diagnostic, "hangi aygit oldugu yazmali"
    assert "JARVIS_MIC_DEVICE" in sonuc.diagnostic, "nasil degistirilecegi yazmali"


def test_real_noise_floor_is_not_called_dead():
    """Sessiz oda olu akis DEGILDIR: gercek mikrofon tam sifir uretmez."""
    sonuc = kaydedici(kaynak(gurultu(200))).record()
    assert sonuc.ok is False
    assert sonuc.reason == "no_speech_detected"
    assert sonuc.diagnostic is None, "gurultu tabani olu sayilmamali"


def test_speech_never_flagged_dead():
    sonuc = kaydedici(kaynak(konusma(5), gurultu(60))).record()
    assert sonuc.ok is True
    assert sonuc.diagnostic is None


def test_dead_diagnostic_reaches_the_listener():
    """Tani VoiceListener'in uyarisina kadar ulasmali."""
    from voice.stt import VoiceListener

    listener = VoiceListener(
        recorder=kaydedici(kaynak(sifir(200)), device=7),
        transcriber=lambda s, sr: pytest.fail("olu akis transkribe edilmemeli"),
    )
    sonuc = listener.listen()
    assert sonuc.ok is False
    assert "dead_audio_stream" in (sonuc.warning or "")


# --------------------------------------------------------------------------- #
# 2. Aygit secimi — belirsiz isim calisan bir GIRIS aygitina dusmeli
# --------------------------------------------------------------------------- #

AYGITLAR = [
    {"name": "Microsoft Ses Eslestiricisi - Input", "max_input_channels": 2},
    {"name": "Mikrofon (HyperX SoloCast)", "max_input_channels": 2},   # 1 MME
    {"name": "Hoparlor (Realtek)", "max_input_channels": 0},           # cikis
    {"name": "Mikrofon (HyperX SoloCast)", "max_input_channels": 2},   # 3 DSound
    {"name": "Mikrofon (HyperX SoloCast)", "max_input_channels": 2},   # 4 WASAPI
]


def secim(spec, acilabilir=(0, 1, 3)):
    from voice.stt import select_input_device

    return select_input_device(
        spec,
        query=lambda: AYGITLAR,
        check=lambda i: i in acilabilir,
    )


def test_none_stays_none():
    assert secim(None) is None


def test_index_passes_through_untouched():
    assert secim(4) == 4, "acik indeks kullanicinin karari, dogrulanmaz"


def test_ambiguous_name_falls_back_to_a_working_input_device():
    """'SoloCast' dort host API'de eslesiyor; sounddevice bunu reddediyor.

    Olculdu: check_input_settings('SoloCast') -> 'Multiple input devices
    found'. Isim atilmaz; ACILABILEN ilk giris aygitina dusulur.
    """
    assert secim("SoloCast") == 1


def test_name_skips_output_devices():
    """Cikis aygiti asla secilmez -- gecen sefer tam bu hata yapildi."""
    assert secim("Hoparlor") is None


def test_name_skips_devices_that_cannot_open():
    """Eslesse bile acilamayan aygit atlanir (WASAPI 16 kHz reddediyor)."""
    assert secim("SoloCast", acilabilir=(3,)) == 3


def test_unmatched_name_returns_none():
    assert secim("YokBoyleAygit") is None


def test_name_match_is_turkish_fold_insensitive():
    assert secim("solocast") == 1
    assert secim("SOLOCAST") == 1


# --------------------------------------------------------------------------- #
# 3. Varsayilan yakalama yolu geri-cagirma kullanmali
# --------------------------------------------------------------------------- #

def test_default_capture_path_uses_callback_not_blocking_read():
    """Bloklayan read() DirectSound'da olu ses donduruyor (olculdu).

    Kaynak metninde `callback=` gecmeli ve `.read(` GECMEMELI.
    """
    import ast
    import inspect
    import textwrap

    from voice.stt import MicrophoneRecorder

    ham = textwrap.dedent(
        inspect.getsource(MicrophoneRecorder._default_chunk_source)
    )
    # Docstring KODA sayilmaz: aciklama metni "read()" kelimesini gecirebilir.
    fn = ast.parse(ham).body[0]
    if (fn.body and isinstance(fn.body[0], ast.Expr)
            and isinstance(fn.body[0].value, ast.Constant)):
        fn.body = fn.body[1:]
    kod = ast.unparse(fn)

    assert "callback" in kod, (
        "varsayilan yol geri-cagirma kullanmali; bloklayan read() bazi host "
        "API'lerinde sessizce olu ses donduruyor"
    )
    assert ".read(" not in kod, "bloklayan read() birakilmis"
