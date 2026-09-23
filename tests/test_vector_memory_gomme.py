"""`koleksiyon_ac` sozlesmesi: gomme modeli degisimi ve sessiz geri dusme.

Ikisi de 2026-09-23'te OLCULDU ve ikisi de sessiz hata sinifindandir --
Chroma hata vermez, sorgu calisir, sayilar makul gorunur.

`chromadb` gerekmez: istemci sahtedir, cunku olculen sey Chroma degil
BIZIM kararimiz (bos mu dolu mu, silinir mi silinmez mi).
"""

from __future__ import annotations

import pytest

from tools.vector_memory import KoleksiyonCakismasi, koleksiyon_ac


class SahteKoleksiyon:
    def __init__(self, sayi=0, gomme=None):
        self._sayi = sayi
        self._embedding_function = gomme

    def count(self):
        if self._sayi < 0:
            raise RuntimeError("sayilamadi")
        return self._sayi


class SahteIstemci:
    """Chroma'nin olculen davranisini taklit eder.

    ``mevcut_gomme`` koleksiyonun DISKTE kayitli modelidir. Farkli bir
    model istenirse Chroma `ValueError` atar -- olculdu.
    """

    def __init__(self, mevcut_gomme=None, mevcut_sayi=0, var=True):
        self.mevcut_gomme = mevcut_gomme
        self.mevcut_sayi = mevcut_sayi
        self.var = var
        self.silinenler: list[str] = []
        #: Chroma'nin sessiz geri dusmesini taklit etmek icin.
        self.zorla_dondur = None

    def get_or_create_collection(self, ad, metadata=None, embedding_function=None):
        if self.var and embedding_function is not None \
                and embedding_function is not self.mevcut_gomme:
            raise ValueError(
                "An embedding function already exists in the collection "
                "configuration, and a new one is provided."
            )
        self.var = True
        self.mevcut_gomme = embedding_function
        if self.zorla_dondur is not None:
            return self.zorla_dondur
        return SahteKoleksiyon(sayi=self.mevcut_sayi, gomme=embedding_function)

    def get_collection(self, ad):
        return SahteKoleksiyon(sayi=self.mevcut_sayi, gomme=self.mevcut_gomme)

    def delete_collection(self, ad):
        self.silinenler.append(ad)
        self.var = False
        self.mevcut_sayi = 0
        self.mevcut_gomme = None


ESKI = object()
YENI = object()


# ── 1. gomme modeli degisimi ─────────────────────────────────────────────


def test_bos_koleksiyon_yeni_modelle_yeniden_kurulur():
    """Bos koleksiyonda kaybedilecek bir sey yok; ucuzken duzeltilir."""
    duyurular: list[str] = []
    istemci = SahteIstemci(mevcut_gomme=ESKI, mevcut_sayi=0)

    col = koleksiyon_ac(istemci, "jarvis_memories", YENI, duyurular.append)

    assert istemci.silinenler == ["jarvis_memories"]
    assert col._embedding_function is YENI
    assert any("yeniden" in d for d in duyurular), duyurular


def test_dolu_koleksiyon_SILINMEZ():
    """Bu kodun veri imha araci olmamasini saglayan tek ayrim."""
    istemci = SahteIstemci(mevcut_gomme=ESKI, mevcut_sayi=7)

    with pytest.raises(KoleksiyonCakismasi) as bilgi:
        koleksiyon_ac(istemci, "jarvis_memories", YENI)

    assert istemci.silinenler == [], "dolu koleksiyon silinmemeliydi"
    assert "7 kayit" in str(bilgi.value)


def test_sayilamayan_koleksiyon_DOLU_varsayilir():
    """Bos oldugunu KANITLAYAMIYORSAK dolu kabul edilir; asimetri lehimize."""
    istemci = SahteIstemci(mevcut_gomme=ESKI, mevcut_sayi=-1)

    with pytest.raises(KoleksiyonCakismasi):
        koleksiyon_ac(istemci, "jarvis_memories", YENI)

    assert istemci.silinenler == []


def test_alakasiz_hata_yutulmaz():
    """Yalniz gomme cakismasi ele alinir; baska ariza yukari cikar."""

    class Bozuk(SahteIstemci):
        def get_or_create_collection(self, ad, metadata=None, embedding_function=None):
            raise RuntimeError("disk dolu")

    with pytest.raises(RuntimeError, match="disk dolu"):
        koleksiyon_ac(Bozuk(), "jarvis_memories", YENI)


def test_ayni_model_istenirse_hicbir_sey_silinmez():
    istemci = SahteIstemci(mevcut_gomme=YENI, mevcut_sayi=12)

    col = koleksiyon_ac(istemci, "jarvis_memories", YENI)

    assert istemci.silinenler == []
    assert col._embedding_function is YENI


# ── 2. sessiz geri dusme ─────────────────────────────────────────────────


def test_sessiz_geri_dusme_yakalanir():
    """Olculdu: EF verilmeden acilan koleksiyon `DefaultEmbeddingFunction`
    kullanir, hata vermez ve sorgu "calisir" -- ama soru vektoru
    belgelerden BASKA bir modelden gelir. Iki model de 384 boyut uretiyor,
    yani boyut hatasi da alinmaz. Tek koruma bu kontrol."""
    istemci = SahteIstemci(mevcut_gomme=None, var=False)
    istemci.zorla_dondur = SahteKoleksiyon(sayi=0, gomme=ESKI)

    with pytest.raises(KoleksiyonCakismasi, match="Sessiz geri"):
        koleksiyon_ac(istemci, "jarvis_memories", YENI)


def test_gomme_verilmezse_dogrulama_yapilmaz():
    """`gomme=None` diyen cagiran Chroma'nin varsayilanini KABUL etmistir."""
    istemci = SahteIstemci(mevcut_gomme=None, var=False)

    col = koleksiyon_ac(istemci, "jarvis_memories", None)

    assert col is not None
