"""Tek bir konuşmayı unutturmanın sözleşmesi (KART_UNUT_SUNU).

Bu özellik **veri siliyor** ve eşleştirmesi olasılıksal. O yüzden burada
asıl kilitlenen şey silmenin çalışması değil, **silmemesi gereken yerde
silmemesi**: onay yoksa, konu yoksa, aday yoksa hiçbir şey gitmez.

`chromadb` gerekmez; anlamsal taraf sahte nesneyle verilir.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

from memory.memory_manager import JarvisMemory, sohbet_anahtari


# ── ortak anahtar ────────────────────────────────────────────────────────


def test_anahtar_bosluk_ve_buyuk_harf_farkini_yutar():
    assert sohbet_anahtari("  Salon  KLİMASI   ne durumda ") == \
        sohbet_anahtari("salon klimasi ne durumda".replace("klimasi", "KLİMASI"))


def test_anahtar_bos_girdide_patlamaz():
    assert sohbet_anahtari(None) == ""
    assert sohbet_anahtari("   ") == ""


# ── veri katmanı: forget_by_keys ─────────────────────────────────────────


def _hafiza(tmp_path, satirlar):
    db = tmp_path / "h.db"
    m = JarvisMemory(db_path=str(db), profile_path=str(tmp_path / "p.json"))
    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT INTO conversations (timestamp, user_message, jarvis_response,"
        " model_used) VALUES (?,?,?,?)",
        satirlar,
    )
    conn.commit()
    conn.close()
    return m, db


def _sorular(db):
    conn = sqlite3.connect(db)
    r = [x[0] for x in conn.execute("SELECT user_message FROM conversations")]
    conn.close()
    return r


def test_eslesen_kayit_siliniyor(tmp_path):
    m, db = _hafiza(tmp_path, [
        ("2026-09-24T10:00", "kartlari koltugun altina koydum", "tamam", "t"),
        ("2026-09-24T10:01", "kahve severim", "not aldim", "t"),
    ])

    silinen = m.forget_by_keys({sohbet_anahtari("kartlari koltugun altina koydum")})

    assert silinen == 1
    assert _sorular(db) == ["kahve severim"]


def test_kopyalarin_hepsi_birlikte_gidiyor(tmp_path):
    """Aynı soru geçmişte 59 kez geçebiliyor (ölçüldü). Biri kalırsa
    unutma yarım kalmıştır."""
    m, db = _hafiza(tmp_path, [
        ("2026-09-24T10:00", "nerede kaldik", "sunda kaldik", "t"),
        ("2026-09-24T10:01", "  NEREDE   kaldik  ", "yine sunda", "t"),
        ("2026-09-24T10:02", "kahve severim", "not aldim", "t"),
    ])

    silinen = m.forget_by_keys({sohbet_anahtari("nerede kaldik")})

    assert silinen == 2
    assert _sorular(db) == ["kahve severim"]


def test_BOS_kume_HICBIR_SEY_silmez(tmp_path):
    """Uzlaştırmadaki asimetrinin aynısı: boş girdi toplu silme emri değildir."""
    m, db = _hafiza(tmp_path, [
        ("2026-09-24T10:00", "kahve severim", "not aldim", "t"),
    ])

    assert m.forget_by_keys(set()) == 0
    assert len(_sorular(db)) == 1


def test_eslesmeyen_anahtar_hicbir_sey_silmez(tmp_path):
    m, db = _hafiza(tmp_path, [
        ("2026-09-24T10:00", "kahve severim", "not aldim", "t"),
    ])

    assert m.forget_by_keys({sohbet_anahtari("hic gecmeyen bir sey")}) == 0
    assert len(_sorular(db)) == 1


def test_profil_ve_olaylar_korunuyor(tmp_path):
    m, db = _hafiza(tmp_path, [
        ("2026-09-24T10:00", "kahve severim", "not aldim", "t"),
    ])
    m.update_profile("name", "Ahmet")
    m.add_event("test", "onemli olay", 9)

    m.forget_by_keys({sohbet_anahtari("kahve severim")})

    assert m.profile.get("name") == "Ahmet"
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    conn.close()


# ── ajan: aday bulma ve unutma ───────────────────────────────────────────


def _vurus(user_msg, anahtar=None, similarity=0.8):
    return {
        "id": "c_1",
        "user_msg": user_msg,
        "jarvis_msg": "cevap",
        "ts": "2026-09-22T20:10:00",
        "similarity": similarity,
        "metadata": {"anahtar": anahtar if anahtar is not None
                     else sohbet_anahtari(user_msg)},
    }


def _ajan(adaylar=None, hafiza_mock=None):
    anlamsal = MagicMock()
    anlamsal.ara.return_value = adaylar if adaylar is not None else []
    anlamsal.temizle.return_value = True

    with (
        patch("agent.local_agent.LocalJarvisAgent._init_ollama"),
        patch("agent.local_agent.LocalJarvisAgent._load_memory", return_value=None),
        patch("agent.local_agent.LocalJarvisAgent._load_tools", return_value={}),
        patch("agent.local_agent.LocalJarvisAgent._load_project_context",
              return_value=""),
        patch("agent.local_agent.LocalJarvisAgent._anlamsal_hafiza_kur",
              return_value=anlamsal),
        patch("memory.memory_manager.JarvisMemory",
              return_value=hafiza_mock or MagicMock(forget_by_keys=lambda k: len(k))),
    ):
        from agent.local_agent import LocalJarvisAgent

        ajan = LocalJarvisAgent()
        ajan.ollama_available = True
        ajan.available_models = ["llama3.1:latest"]
        return ajan, anlamsal


def test_konusuz_unut_HICBIR_SEY_silmez():
    """Sadece "unut" demek "her şeyi unut" değildir; onun adı `temizle`."""
    hafiza = MagicMock()
    ajan, anlamsal = _ajan(hafiza_mock=hafiza)

    assert ajan.unutma_adaylari("") == []
    assert ajan.unutma_adaylari("   ") == []
    anlamsal.ara.assert_not_called()
    hafiza.forget_by_keys.assert_not_called()


def test_aday_yoksa_hicbir_sey_silinmez():
    hafiza = MagicMock()
    ajan, _ = _ajan(adaylar=[], hafiza_mock=hafiza)

    assert ajan.unutma_adaylari("klima") == []
    hafiza.forget_by_keys.assert_not_called()


def test_aday_bulma_SILMEZ():
    """Aday bulmak ile silmek ayrı iki adım; arada onay var."""
    hafiza = MagicMock()
    ajan, _ = _ajan(adaylar=[_vurus("kartlari koltugun altina koydum")],
                    hafiza_mock=hafiza)

    adaylar = ajan.unutma_adaylari("devre kartlari nerede")

    assert len(adaylar) == 1
    hafiza.forget_by_keys.assert_not_called(), "aday bulma silmemeli"


def test_unut_IKI_YERDEN_birden_siler():
    """SQLite yeterli degil: indeks kalirsa unutulan konusma bir sonraki
    turda anlamsal aramayla geri gelir -- B04'un ayni tuzagi."""
    hafiza = MagicMock()
    hafiza.forget_by_keys.return_value = 3
    ajan, anlamsal = _ajan(hafiza_mock=hafiza)
    anlamsal.unut_anahtarlari.return_value = 2

    sonuc = ajan.unut({"a", "b"})

    assert sonuc == 3
    hafiza.forget_by_keys.assert_called_once_with({"a", "b"})
    anlamsal.unut_anahtarlari.assert_called_once_with({"a", "b"})


def test_indeks_silinemezse_kullanici_uyarilir():
    """Yarim unutma SESSIZ gecmez."""
    hafiza = MagicMock()
    hafiza.forget_by_keys.return_value = 1
    ajan, anlamsal = _ajan(hafiza_mock=hafiza)
    anlamsal.unut_anahtarlari.return_value = 0
    duyurular = []
    ajan._notify = duyurular.append

    ajan.unut({"a"})

    assert any("dizin" in d for d in duyurular), duyurular


def test_unut_bos_secimde_hicbir_sey_yapmaz():
    hafiza = MagicMock()
    ajan, _ = _ajan(hafiza_mock=hafiza)

    assert ajan.unut(set()) == 0
    hafiza.forget_by_keys.assert_not_called()


def test_aday_anahtari_ustveriden_gelir_kirpilmis_metinden_degil():
    """Üstverideki `user_msg` 200 karaktere kırpılmış; uzun bir soruda
    anahtarı ondan türetmek eşleşmeyi kaçırırdı."""
    uzun = "x" * 400
    aday = _vurus(uzun[:200], anahtar=sohbet_anahtari(uzun))
    ajan, _ = _ajan(adaylar=[aday])

    bulunan = ajan.unutma_adaylari("bir sey")

    assert bulunan[0]["anahtar"] == sohbet_anahtari(uzun)
