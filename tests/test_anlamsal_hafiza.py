"""Anlamsal sohbet hafizasinin sozlesmesi (KART_VEKTOR_HAFIZA ADIM 1-2).

Bu testler `chromadb` GEREKTIRMEZ: kapi (CLAUDE.md 13.2) sistem
Python'unda kosuyor ve orada chromadb kurulu degil. Depo her yerde
sahte bir nesneyle verilir -- zaten olculmek istenen sey Chroma degil,
**bizim** kapilarimiz.
"""

from __future__ import annotations

from agent.anlamsal_hafiza import SOHBET_KOLEKSIYONU, AnlamsalHafiza


class SahteDepo:
    """`VectorMemory`nin bu yolda kullanilan yuzeyi kadari."""

    def __init__(self, sonuclar=None, patla=False):
        self.sonuclar = sonuclar if sonuclar is not None else []
        self.patla = patla
        self.cagrilar: list[tuple] = []
        self.reset_sayisi = 0
        self.reset_sonucu = True
        self.yazilanlar: list[tuple] = []
        self.collection_name = SOHBET_KOLEKSIYONU

    def find_similar(self, query, n=3, threshold=0.7):
        self.cagrilar.append((query, n, threshold))
        if self.patla:
            raise RuntimeError("chroma coktu")
        return list(self.sonuclar)

    def remember(self, user_msg, jarvis_msg, meta=None):
        self.yazilanlar.append((user_msg, jarvis_msg, meta))
        return "id_1"

    def stats(self):
        return {"total": len(self.sonuclar)}

    def reset(self):
        self.reset_sayisi += 1
        return self.reset_sonucu


def _hazir(depo=None, **kw) -> tuple[AnlamsalHafiza, SahteDepo]:
    depo = depo or SahteDepo()
    h = AnlamsalHafiza(fabrika=lambda: depo, **kw)
    h.isit()
    assert h.bekle(5), f"isinma bitmedi: {h.durum} {h.hata}"
    return h, depo


def _vurus(similarity=0.80, **meta):
    taban = {
        "memory_action": "keep_long_term",
        "memory_type": "semantic",
        "storage_target": "vector",
        "sensitivity": "normal",
    }
    taban.update(meta)
    return {
        "id": "c_1",
        "user_msg": "salon klimasinin kablosu cikmisti",
        "jarvis_msg": "kabloyu taktiginizda olcumler geri geldi efendim",
        "ts": "2026-09-22T20:10:00",
        "similarity": similarity,
        "metadata": taban,
    }


# ── kurulum ve arizalar ──────────────────────────────────────────────────


def test_depo_kurulamazsa_cokmez_ve_bos_doner():
    """chromadb yoksa sohbet DURMAZ. Hafiza bir kolayliktir."""
    duyurular: list[str] = []

    def patlayan_fabrika():
        raise ImportError("pip install chromadb")

    h = AnlamsalHafiza(fabrika=patlayan_fabrika, duyur=duyurular.append)
    h.isit()
    h.bekle(5)

    assert h.durum == "yok"
    assert h.hazir() is False
    assert h.ara("salon klimasi ne durumda") == []
    assert h.prompt_blogu("salon klimasi ne durumda") == ""
    assert duyurular, "ariza sessiz gecmemeli"


def test_isinmadan_once_beklemez_bos_doner():
    """Model yuklemesi 13 saniye surer; sohbet yolu onu BEKLEMEZ."""
    h = AnlamsalHafiza(fabrika=lambda: SahteDepo([_vurus()]))
    # isit() cagrilmadi: henuz "bekliyor" durumunda.
    assert h.hazir() is False
    assert h.ara("salon klimasi") == []
    assert h.prompt_blogu("salon klimasi") == ""


def test_arama_patlarsa_bos_doner_ve_duyurur():
    duyurular: list[str] = []
    h, _ = _hazir(SahteDepo(patla=True), duyur=duyurular.append)

    assert h.ara("salon klimasi ne durumda") == []
    assert any("arama" in d for d in duyurular)


def test_cok_kisa_sorgu_aramaz():
    h, depo = _hazir(SahteDepo([_vurus()]))

    assert h.ara("ok") == []
    assert depo.cagrilar == [], "kisa sorgu icin depoya hic gidilmemeli"


# ── olcek donusumu ───────────────────────────────────────────────────────


def test_benzerlik_esigi_uzakliga_cevrilir():
    """`find_similar` KOSINUS UZAKLIGI bekler (kucuk iyi), biz BENZERLIK
    tutariz (buyuk iyi). Donusum tek yerde yapilmazsa iki olcek zamanla
    birbirinin tersine suruklenir."""
    h, depo = _hazir(SahteDepo([_vurus()]), esik=0.45, n=4)

    h.ara("salon klimasinin durumu ne")

    sorgu, n, threshold = depo.cagrilar[0]
    assert n == 4
    assert abs(threshold - 0.55) < 1e-9, threshold


# ── politika kapisi ──────────────────────────────────────────────────────


def test_hassas_kayit_prompta_girmez():
    hassas = _vurus(sensitivity="sensitive")
    h, _ = _hazir(SahteDepo([hassas]))

    assert h.ara("salon klimasinin durumu ne") == []


def test_onay_bekleyen_kayit_prompta_girmez():
    bekleyen = _vurus(status="pending_review")
    h, _ = _hazir(SahteDepo([bekleyen]))

    assert h.ara("salon klimasinin durumu ne") == []


def test_esigin_altindaki_kayit_elenir():
    h, _ = _hazir(SahteDepo([_vurus(similarity=0.20)]), esik=0.45)

    assert h.ara("salon klimasinin durumu ne") == []


def test_politika_patlarsa_hafiza_KULLANILMAZ():
    """Guard arizasi kapiyi ACMAZ, KAPATIR (Codex B10 dersi)."""

    class PatlayanPolitika:
        def filter_hits(self, hits, query=""):
            raise RuntimeError("politika bozuk")

    duyurular: list[str] = []
    h, _ = _hazir(
        SahteDepo([_vurus()]),
        politika=PatlayanPolitika(),
        duyur=duyurular.append,
    )

    assert h.ara("salon klimasinin durumu ne") == []
    assert any("politika" in d for d in duyurular)


def test_temiz_kayit_gecer():
    h, _ = _hazir(SahteDepo([_vurus()]))

    sonuc = h.ara("salon klimasinin durumu ne")

    assert len(sonuc) == 1
    assert sonuc[0]["id"] == "c_1"


# ── prompt blogu ─────────────────────────────────────────────────────────


def test_bulunan_yoksa_blok_bostur():
    """Bos zemin, yanlis zeminden iyidir."""
    h, _ = _hazir(SahteDepo([]))

    assert h.prompt_blogu("hic eslesmeyen bir soru") == ""


def test_blok_bulunani_ve_uyarisini_icerir():
    h, _ = _hazir(SahteDepo([_vurus()]))

    blok = h.prompt_blogu("salon klimasinin durumu ne")

    assert "GECMIS KONUSMALARDAN" in blok
    assert "salon klimasinin kablosu cikmisti" in blok
    assert "2026-09-22" in blok
    # Canli durumun ustunlugu YAZILI olmali: yoksa model eski bir cumleyi
    # bugunun olgusu gibi tekrar eder (PUSULA ihlali).
    assert "GUNCEL" in blok


def test_bos_icerikli_kayit_blok_uretmez():
    bos = _vurus()
    bos["user_msg"] = ""
    bos["jarvis_msg"] = ""
    h, _ = _hazir(SahteDepo([bos]))

    assert h.prompt_blogu("salon klimasinin durumu ne") == ""


# ── indeks bakimi ────────────────────────────────────────────────────────


def test_sohbet_indeksi_ayri_koleksiyonda_durur():
    """7.1a: onaylanmis bilgi kartlari `jarvis_memories`'te durur ve bu
    modul oraya ASLA yazmaz. Ayni koleksiyon paylasilsaydi `clear_history`
    onaylanmis kartlari da silerdi."""
    assert SOHBET_KOLEKSIYONU != "jarvis_memories"


def test_temizle_indeksi_siler():
    h, depo = _hazir(SahteDepo([_vurus()]))

    assert h.temizle() is True
    assert depo.reset_sayisi == 1


def test_temizle_basarisizligi_yutulmaz():
    depo = SahteDepo([_vurus()])
    depo.reset_sonucu = False
    h, _ = _hazir(depo)

    assert h.temizle() is False


def test_sohbet_yolu_indekse_yazmaz():
    """`ara`/`prompt_blogu` OKUR; yazma yalniz backfill betiginindir."""
    h, depo = _hazir(SahteDepo([_vurus()]))

    h.ara("salon klimasinin durumu ne")
    h.prompt_blogu("salon klimasinin durumu ne")

    assert depo.yazilanlar == []
