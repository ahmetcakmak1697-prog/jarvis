"""`dogrula` sondasının karar mantığı (KART_STT_DOGRULA ADIM 2-3).

Ses gerektiren kısım burada sınanmaz; sınanan şey **hükmü veren iki saf
fonksiyon**. Kartın kritik sorusu ölçümün kendisi değil, ölçümden çıkarılan
sonuç: "Hey Jarvis" duyuldu mu sayılacak, ve gürültüdeki uydurma **ipucu
yüzünden mi arttı** yoksa zaten var mıydı.

`faster_whisper` gerekmez.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from olc_stt_turkce import (  # noqa: E402
    IPUCU_KELIMELER,
    sizinti_farki,
    uyandirma_duyuldu,
)


# ── "Hey Jarvis" duyuldu mu ──────────────────────────────────────────────


def test_tam_cumle_duyuldu():
    s = uyandirma_duyuldu("Hey Jarvis, nerede kaldık?")

    assert s["jarvis"] is True
    assert s["hey_jarvis"] is True


def test_olculen_gercek_hata_duymamis_sayilir():
    """Ölçülen kusur buydu: `small`/1 bu cümleyi "Heyecan mısın?" duyuyor
    ve içinde "jarvis" hiç geçmiyor."""
    s = uyandirma_duyuldu("Heyecan mısın?")

    assert s["jarvis"] is False
    assert s["hey_jarvis"] is False


def test_jarvis_var_ama_hey_yok_ayri_raporlanir():
    """İkisi ayrı sayılır: "Jarvis" duymak uyandırma için yeterli olabilir,
    ama tam cümleyi duymakla aynı şey değildir. Hangisi olduğu görünsün."""
    s = uyandirma_duyuldu("Jarvis nerede kaldık")

    assert s["jarvis"] is True
    assert s["hey_jarvis"] is False


def test_buyuk_harf_ve_noktalama_fark_etmez():
    assert uyandirma_duyuldu("HEY JARVIS!!! nerede kaldık")["hey_jarvis"] is True


def test_turkce_I_tuzagina_dusmez():
    """CLAUDE.md §6: düz `.lower()` "İ" için birleşik noktalı karakter
    üretir ve eşleşme sessizce kaçar."""
    assert uyandirma_duyuldu("HEY JARVİS nerede kaldık")["jarvis"] is True


def test_bos_metin_duymamis_sayilir():
    s = uyandirma_duyuldu("")

    assert s["jarvis"] is False
    assert s["hey_jarvis"] is False


# ── sızıntı: ipucunun FARKI ──────────────────────────────────────────────


def test_ipucu_kelimesi_yalniz_ipucluda_cikarsa_isaretlenir():
    """Kartın asıl sorusu bu: uydurma ipucu yüzünden mi arttı?"""
    f = sizinti_farki("bu dizinin betimlemesi", "jarvis ollama commit",
                      IPUCU_KELIMELER)

    # Rapor ipucu LISTESINDEKI yazimi doner; boylece hangi kelimenin
    # sizdigi listeyle birebir karsilastirilabilir.
    assert set(f["ipuclu_gorunen"]) == {"Jarvis", "Ollama", "commit"}
    assert set(f["yalniz_ipucluda"]) == {"Jarvis", "Ollama", "commit"}


def test_zaten_var_olan_uydurma_ipucuya_YAZILMAZ():
    """Whisper ipucusuz da uyduruyor. Ölçülen şey ipucunun farkı."""
    f = sizinti_farki("jarvis diyor", "jarvis diyor", IPUCU_KELIMELER)

    assert set(f["ipuclu_gorunen"]) == {"Jarvis"}
    assert f["yalniz_ipucluda"] == [], "ipucusuzda da vardi, ipucuya yazilmaz"


def test_temiz_iki_satir_sizinti_uretmez():
    f = sizinti_farki("", "", IPUCU_KELIMELER)

    assert f["ipuclu_gorunen"] == []
    assert f["yalniz_ipucluda"] == []
    assert f["ipucusuz_gorunen"] == []


def test_ipucusuzda_olup_ipucluda_olmayan_da_gorunur():
    """Tek yön ölçmek yanıltır: ipucu bir uydurmayı BASTIRMIŞ da olabilir."""
    f = sizinti_farki("klima sesi", "", IPUCU_KELIMELER)

    assert set(f["ipucusuz_gorunen"]) == {"klima"}
    assert f["yalniz_ipucluda"] == []


def test_ipucu_listesi_BUYUTULMEZ():
    """Kart aynı beş kelimeyi sınıyor; genişletmek ayrı bir ölçüm."""
    assert IPUCU_KELIMELER == ("Jarvis", "DeepSeek", "Ollama", "commit", "klima")
