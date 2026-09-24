"""İndeks uzlaştırma kararının sözleşmesi (KART_INDEKS_UZLASTIRMA).

Ölçülen şey Chroma değil **bizim kararımız**: hangi kimlikler silinecek ve
hangi durumda hiç silinmeyecek. Bu yüzden saf bir fonksiyon sınanır ve
`chromadb` gerekmez — kapı (CLAUDE.md §13.2) sistem Python'unda koşuyor ve
orada kurulu değil.

Kartın en kritik maddesi burada: "SQLite'ta olmayan her şeyi sil" emri,
SQLite boş okunduğu anda "indeksin tamamını sil" demektir.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import hafiza_indeksle  # noqa: E402
from hafiza_indeksle import uzlastir_plani  # noqa: E402


# ── normal yol ───────────────────────────────────────────────────────────


def test_silinen_konusma_indeksten_dusuyor():
    plan = uzlastir_plani(gecerli={"a", "b"}, mevcut={"a", "b", "c"})

    assert plan.silinecek == {"c"}
    assert plan.durma is None


def test_duzenlenen_kayit_oksuz_birakmiyor():
    """Kimlik içerikten türediği için metin değişince YENİ kimlik oluşur.

    Eski kayıt aynı mekanizmayla düşmeli; yoksa bir konuşmanın iki sürümü
    indekste yan yana durur ve arama eskisini getirebilir.
    """
    plan = uzlastir_plani(gecerli={"a", "b_yeni"}, mevcut={"a", "b_eski"})

    assert plan.silinecek == {"b_eski"}
    assert plan.durma is None


def test_fazlalik_yoksa_hicbir_sey_silinmez():
    plan = uzlastir_plani(gecerli={"a", "b"}, mevcut={"a", "b"})

    assert plan.silinecek == set()
    assert plan.durma is None


def test_indeks_bossa_sorunsuz():
    plan = uzlastir_plani(gecerli={"a"}, mevcut=set())

    assert plan.silinecek == set()
    assert plan.durma is None


# ── asıl koruma: boş okuma indeksi SİLDİRMEZ ─────────────────────────────


def test_bos_gecerli_kume_HICBIR_SEY_sildirmez():
    """Kartın en önemli maddesi.

    SQLite okunamaz ya da boş dönerse "orada olmayanı sil" emri indeksin
    tamamını silmek olurdu. `koleksiyon_ac`'taki asimetrinin aynısı:
    boş olduğunu KANITLAYAMIYORSAK dokunmayız.
    """
    plan = uzlastir_plani(gecerli=set(), mevcut={"a", "b", "c"})

    assert plan.silinecek == set(), "bos okuma indeksi silmemeli"
    assert plan.durma is not None
    assert "bos" in plan.durma.lower()


def test_bos_kume_bos_indeks_de_guvenli():
    plan = uzlastir_plani(gecerli=set(), mevcut=set())

    assert plan.silinecek == set()


# ── ikinci emniyet: yarıdan fazlası ──────────────────────────────────────


def test_yaridan_fazlasi_silinecekse_DURUR():
    """Normal kullanımda bir seferde bu kadar kayıt düşmez; düşüyorsa
    okuma tarafında bir şey bozulmuştur."""
    plan = uzlastir_plani(gecerli={"a"}, mevcut={"a", "b", "c", "d"})

    assert plan.silinecek == set(), "durduysa silmemeli"
    assert plan.durma is not None
    assert "yari" in plan.durma.lower()


def test_tam_yari_gecer():
    """Sınır açıkça yazılı: ASAN durur, tam yarı geçer."""
    plan = uzlastir_plani(gecerli={"a", "b"}, mevcut={"a", "b", "c", "d"})

    assert plan.silinecek == {"c", "d"}
    assert plan.durma is None


def test_durma_sebebi_cozumu_soyluyor():
    """Sessiz reddetme yok: kullanıcı ne yapacağını bilmeli."""
    plan = uzlastir_plani(gecerli={"a"}, mevcut={"a", "b", "c", "d"})

    assert "--sil" in plan.durma, plan.durma


# ── sayım ────────────────────────────────────────────────────────────────


def test_plan_sayilari_tasiyor():
    """Uzlaştırmanın çalıştığı SAYIYLA gösterilir, iddiayla değil."""
    plan = uzlastir_plani(gecerli={"a", "b", "yeni"}, mevcut={"a", "b", "c"})

    assert plan.eklenecek == {"yeni"}
    assert plan.silinecek == {"c"}
    assert plan.degismeyen == {"a", "b"}


# ── varsayılan argüman tuzağı ────────────────────────────────────────────


def _db_kur(yol, satirlar):
    import sqlite3

    c = sqlite3.connect(yol)
    c.execute(
        "CREATE TABLE conversations (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " timestamp TEXT, user_message TEXT, jarvis_response TEXT,"
        " model_used TEXT)"
    )
    c.executemany(
        "INSERT INTO conversations (timestamp, user_message, jarvis_response,"
        " model_used) VALUES (?,?,?,?)",
        satirlar,
    )
    c.commit()
    c.close()


def test_VERITABANI_degistirilince_gercekten_o_okunur(tmp_path, monkeypatch):
    """Python varsayılan argümanı TANIM anında bağlar.

    İmza `db: Path = VERITABANI` yazıldığında modül değişkenini sonradan
    değiştirmek hiçbir işe yaramıyordu: fonksiyon her zaman üretim
    veritabanını okuyordu. Bir doğrulama betiği tam bu yüzden geçici
    kopyayı işaret ettiğini sanıp gerçek veriyi ölçtü — sessizce yanlış
    sonuç üreten cinsten bir tuzak.
    """
    sahte = tmp_path / "sahte.db"
    _db_kur(sahte, [("2026-09-24T10:00:00", "denek sorusu burada",
                     "denek cevabi burada efendim", "test")])
    monkeypatch.setattr(hafiza_indeksle, "VERITABANI", sahte)

    kayitlar = hafiza_indeksle.kayitlari_oku(sessiz=True)

    assert len(kayitlar) == 1, "modul degiskeni dikkate alinmadi"
    assert kayitlar[0]["soru"] == "denek sorusu burada"


def test_acik_yol_da_calisir(tmp_path):
    sahte = tmp_path / "acik.db"
    _db_kur(sahte, [("2026-09-24T10:00:00", "acik yoldan okunan soru",
                     "acik yoldan okunan cevap", "test")])

    kayitlar = hafiza_indeksle.kayitlari_oku(db=sahte, sessiz=True)

    assert len(kayitlar) == 1


def test_bos_tablo_bos_liste_dondurur(tmp_path):
    """İndeksi silmemenin ilk halkası: okuma boş dönerse boş döner."""
    sahte = tmp_path / "bos.db"
    _db_kur(sahte, [])

    assert hafiza_indeksle.kayitlari_oku(db=sahte, sessiz=True) == []
