"""CumleTamponu -- akan metni TTS'e verilebilir cumlelere boler.

NEDEN BU TEST ONCE YAZILDI: cumle sonu tespiti Turkce'de naif nokta
aramasiyla yapilamaz. Bu panelin/ajanin gercek cikti ornekleri:

  "Oda 25.5 derece."      -> 25.5'teki nokta cumle sonu DEGIL
  "Saat 21.30'da geldim." -> ayni tuzak
  "Dr. Ahmet aradi."      -> kisaltma noktasi cumle sonu DEGIL
  "vs. gibi seyler."      -> ayni
  "Efendim..."            -> uc nokta TEK cumle sonu

Yanlis bolme TTS'i cumlenin ortasinda konusturur; hic bolmemek ise akisi
olduruq tek parca bekletir. Ikisi de kullanicinin duydugu seyi bozar.
"""
from __future__ import annotations

import pytest

from voice.cumle_tamponu import CumleTamponu


def topla(parcalar):
    """Parcalari sirayla besle, cikan cumleleri dondur (son akis dahil)."""
    t = CumleTamponu()
    cikan = []
    for p in parcalar:
        cikan.extend(t.besle(p))
    cikan.extend(t.bitir())
    return cikan


def test_tek_parca_tek_cumle():
    assert topla(["Merhaba efendim."]) == ["Merhaba efendim."]


def test_parcali_gelen_cumle_birlestirilir():
    # Model kelime kelime akitir; tampon tam cumleyi beklemeli.
    assert topla(["Mer", "haba ", "efen", "dim."]) == ["Merhaba efendim."]


def test_iki_cumle_ayri_ayri_verilir():
    assert topla(["Merhaba. Nasilsin?"]) == ["Merhaba.", "Nasilsin?"]


def test_cumle_tamamlanmadan_hicbir_sey_verilmez():
    t = CumleTamponu()
    assert t.besle("Merhaba efen") == []
    assert t.besle("dim") == []
    assert t.besle(".") == ["Merhaba efendim."]


@pytest.mark.parametrize("metin", [
    "Oda 25.5 derece.",
    "Saat 21.30'da geldim.",
    "Toplam 1621.27 kWh harcandi.",
])
def test_ondalik_sayidaki_nokta_cumle_sonu_degil(metin):
    """Rakam-nokta-rakam bir sayidir. Panelde her deger boyle geliyor."""
    assert topla([metin]) == [metin]


@pytest.mark.parametrize("metin", [
    "Dr. Ahmet aradi.",
    "Saat 9 gibi vs. seyler oldu.",
    "Bkz. ikinci madde.",
])
def test_kisaltmadaki_nokta_cumle_sonu_degil(metin):
    assert topla([metin]) == [metin]


def test_uc_nokta_tek_cumle_sonudur():
    assert topla(["Efendim... Buyurun."]) == ["Efendim...", "Buyurun."]


def test_soru_ve_unlem_cumle_sonudur():
    assert topla(["Nasilsin? Iyiyim! Peki."]) == ["Nasilsin?", "Iyiyim!", "Peki."]


def test_bitir_yarim_kalani_da_verir():
    """Model noktalama koymadan bitirebilir; soylenmeden kalmasin."""
    t = CumleTamponu()
    assert t.besle("Yarim kalan bir cumle") == []
    assert t.bitir() == ["Yarim kalan bir cumle"]


def test_bitir_bosken_bos_doner():
    t = CumleTamponu()
    assert t.bitir() == []
    assert t.bitir() == []          # idempotent


def test_bos_parca_bir_sey_yapmaz():
    t = CumleTamponu()
    assert t.besle("") == []
    assert t.besle("Tamam.") == ["Tamam."]


def test_bosluk_kirpilir_ama_ic_bosluk_korunur():
    assert topla(["  Merhaba   dostum.  "]) == ["Merhaba   dostum."]


def test_turkce_karakterler_bozulmaz():
    m = "Işıkları kapat, perdeyi indir. Klimayı 24'e ayarla."
    assert topla([m]) == ["Işıkları kapat, perdeyi indir.", "Klimayı 24'e ayarla."]


def test_asiri_uzun_noktalamasiz_metin_zorla_bolunur():
    """Model noktalama koymadan uzun konusursa TTS hic baslamaz.
    Guvenlik valfi: sinir asilinca son bosluktan bolunur."""
    uzun = "kelime " * 80                      # ~560 karakter, hic noktalama
    cikan = topla([uzun])
    assert len(cikan) >= 2
    assert "".join(c + " " for c in cikan).split() == uzun.split()
