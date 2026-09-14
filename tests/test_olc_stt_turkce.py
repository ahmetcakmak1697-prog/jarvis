"""KART_STT_TURKCE -- STT sondasinin olcum cekirdegi.

Sondanin iki isi var ve ikisi de burada kilitlenir:

* WER: Turkce'de ASCII-fold UYGULANMAZ -- "s" ile "ş" farkli kelimedir ve
  bu olcumun konusu tam olarak odur. Ama buyuk/kucuk harf ve noktalama bir
  tanima hatasi degildir: "İ" -> "i", "I" -> "ı" (duz `.lower()` "İ"yi
  "i" + birlesik nokta yapar, CLAUDE.md §6) ve kesme isareti atilir
  ("İstanbul'da" ile "İstanbulda" ayni kelimedir).
* Kusur B: uretim kaydedicisi (voice/stt.py `MicrophoneRecorder`) kayit
  uzerinde YENIDEN OYNATILIR -- mantigi kopyalanmaz. Yumusak konusma esigin
  altinda kalirsa cumle erken kesilir; sonda bunu olcer.

Ses kayitlari Ahmet'in sesidir; sonda repo icine yazmayi REDDEDER.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from olc_stt_turkce import (
    CUMLELER,
    normalize_tr,
    repo_disinda,
    sessizlik_simulasyonu,
    wer,
)

KOK = Path(__file__).resolve().parents[1]
ORNEKLEME = 16000


def _sinyal(*bolumler):
    """(saniye, genlik) bolumlerinden sabit genlikli ornek dizisi."""
    ornekler = []
    for saniye, genlik in bolumler:
        ornekler.extend([genlik] * int(saniye * ORNEKLEME))
    return ornekler


# --- 1. WER --------------------------------------------------------------- #

def test_ayni_metin_sifir_hata():
    assert wer("Hey Jarvis, nerede kaldık?", "hey jarvis nerede kaldık")["hata"] == 0


def test_canli_gozlem_merhaba_mahbubar_bir_kelime_hatasi():
    """2026-09-14 canli oturumu: "Merhaba" -> "Mahbubar"."""
    s = wer("Merhaba dostum iyi misin?", "Mahbubar dostum iyi misin?")
    assert (s["hata"], s["kelime"]) == (1, 4)
    assert s["oran"] == pytest.approx(0.25)


def test_ascii_fold_uygulanmaz():
    """"ş" ile "s" farkli kelimedir -- olcumun konusu tam olarak bu."""
    assert wer("Işıkları kapat", "Isiklari kapat")["hata"] == 1


def test_turkce_buyuk_harf_kurali():
    assert normalize_tr("İYİ Mİ? IŞIK") == ["iyi", "mi", "ışık"]


def test_noktalama_ve_kesme_isareti_tanima_hatasi_degil():
    assert wer("İstanbul'da hava nasıl?", "istanbulda hava nasıl")["hata"] == 0


def test_ekleme_ve_silme_sayilir():
    assert wer("nerede kaldık", "hey nerede")["hata"] == 2


def test_bos_hipotez_her_kelimeyi_kaybeder():
    s = wer("merhaba dostum", "")
    assert (s["hata"], s["oran"]) == (2, 1.0)


# --- 2. Cumle seti -------------------------------------------------------- #

def test_cumle_seti_kartin_istedigini_kapsar():
    """10-15 cumle; ş, ğ, ı, İ gecer; rakam YOK (WER'i "22" / "yirmi iki"
    yazim farki bozmasin)."""
    assert 10 <= len(CUMLELER) <= 15
    butun = " ".join(CUMLELER)
    for harf in ("ş", "ğ", "ı", "İ"):
        assert harf in butun, harf
    assert not any(ch.isdigit() for ch in butun)


# --- 3. Ses repoya girmez ------------------------------------------------- #

def test_repo_icine_ses_yazilmaz(tmp_path):
    with pytest.raises(ValueError):
        repo_disinda(KOK / "automation" / "stt_kayit")
    assert repo_disinda(tmp_path) == tmp_path.resolve()


# --- 4. Kusur B: uretim kaydedicisi kayit uzerinde ------------------------ #

#: sessizlik -> konusma -> yumusak konusma (2 s) -> konusma -> sessizlik
_YUMUSAK_ARA = _sinyal((0.5, 0.002), (1.0, 0.05), (2.0, 0.005),
                       (1.0, 0.05), (2.0, 0.001))


def test_yumusak_konusma_esigin_altindaysa_cumle_erken_kesilir():
    s = sessizlik_simulasyonu(_YUMUSAK_ARA, esik=0.01)
    assert s["basladi"] and s["erken_kesildi"]
    assert s["atilan_esik_ustu_parca"] > 0


def test_esik_dusunce_ayni_cumle_kesilmez():
    s = sessizlik_simulasyonu(_YUMUSAK_ARA, esik=0.003)
    assert s["basladi"] and not s["erken_kesildi"]
    assert s["atilan_esik_ustu_parca"] == 0


def test_esik_ustu_parca_yoksa_konusma_hic_baslamaz():
    """Canli oturumun ucuncu turu: `stt_no_input: no_speech_detected`."""
    s = sessizlik_simulasyonu(_sinyal((3.0, 0.005)), esik=0.01)
    assert not s["basladi"]


# --- 5. Testler mikrofon acmaz, model indirmez ---------------------------- #

def test_sonda_agir_kutuphaneleri_modul_duzeyinde_import_etmez():
    agac = ast.parse((KOK / "scripts" / "olc_stt_turkce.py").read_text(encoding="utf-8"))
    ust = set()
    for dugum in agac.body:
        if isinstance(dugum, ast.Import):
            ust |= {a.name.split(".")[0] for a in dugum.names}
        elif isinstance(dugum, ast.ImportFrom) and dugum.module:
            ust.add(dugum.module.split(".")[0])
    assert not ust & {"sounddevice", "faster_whisper", "numpy"}, ust
