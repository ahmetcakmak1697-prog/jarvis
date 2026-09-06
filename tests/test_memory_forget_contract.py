"""B04 -- "temizle" gercekten temizlemeli, hassas veri kalici depoya girmemeli.

Codex basmuhendis denetimi (2026-09-06), iki ayri kusur:

1. **Kalici depo sinifsiz yaziyordu.** `agent/local_agent.py` 10 karakterden
   uzun her mesaji ve cevabi `JarvisMemory.add_conversation` uzerinden
   SQLite'a yaziyordu. Buna karsilik `LifeGraph` hassas olgulari saklamadigini
   bildiriyor -- ikinci koruma, ilk depodaki HAM konusmayi engellemiyor.

2. **`clear_history()` yalan soyluyordu.** Yalniz RAM listesini ve sayaclari
   sifirliyor, ekrana "Gecmis temizlendi." yaziyordu. Codex'in deneyinde
   temizleme sonrasi RAM 0 oldu ama veritabaninda konusma KALDI ve isaret
   `get_context_for_prompt` ile bir sonraki prompt'a geri girdi.

Ikincisi bir guven sorunudur: kullanici "unut" diyor, JARVIS "unuttum" diyor,
ve bir sonraki turda hatirliyor. Bir asistanin verebilecegi en kotu cevap
"unuttum" deyip unutmamaktir.

Testler GERCEK hafizaya dokunmaz: her vaka kendi gecici veritabaniyla calisir.
"""
from __future__ import annotations

#: Sentetik isaretci -- gercek bir sir degil. `RedactionGuard` `parola=...`
#: bicimini hassas sayiyor (olculdu 2026-09-06).
SIR = "FAKE_AUDIT_MARKER_7719"
HASSAS_MESAJ = f"parola={SIR} olarak ayarladim"
NORMAL_MESAJ = "Yarin saat onda toplantim var, hatirlatir misin"


def _hafiza(tmp_path):
    """Gercek JarvisMemory, gecici dosyalarla."""
    from memory.memory_manager import JarvisMemory

    return JarvisMemory(
        db_path=str(tmp_path / "test_memory.db"),
        profile_path=str(tmp_path / "test_profile.json"),
    )


def _ham_veritabani_metni(hafiza) -> str:
    """Veritabaninda GERCEKTEN ne yaziyor? Uygulama katmanini atlar."""
    import sqlite3

    conn = sqlite3.connect(hafiza.db_path)
    try:
        satirlar = conn.execute(
            "SELECT user_message, jarvis_response FROM conversations"
        ).fetchall()
    finally:
        conn.close()
    return " ".join(str(x) for satir in satirlar for x in satir)


# --------------------------------------------------------------------------- #
# 1. Hassas veri kalici depoya HAM girmemeli
# --------------------------------------------------------------------------- #

def test_hassas_konusma_ham_haliyle_diske_yazilmaz(tmp_path):
    """`parola=...` iceren konusma SQLite'a oldugu gibi yazilmaz."""
    h = _hafiza(tmp_path)
    h.add_conversation(HASSAS_MESAJ, "Tamamdir efendim.")

    assert SIR not in _ham_veritabani_metni(h), (
        "ham sir kalici depoya yazildi"
    )


def test_hassas_cevap_da_temizlenir(tmp_path):
    """Sir kullanicinin degil JARVIS'in cumlesindeyse de yazilmaz."""
    h = _hafiza(tmp_path)
    h.add_conversation("Parolami hatirlat", f"parola={SIR} efendim.")

    assert SIR not in _ham_veritabani_metni(h)


def test_normal_konusma_bozulmadan_kaydedilir(tmp_path):
    """Kapi her seyi kirpmamali -- gunluk hafiza calismaya devam etmeli."""
    h = _hafiza(tmp_path)
    h.add_conversation(NORMAL_MESAJ, "Not aldim efendim.")

    metin = _ham_veritabani_metni(h)
    assert "toplantim var" in metin, "normal konusma bozuldu"
    assert "Not aldim efendim." in metin


# --------------------------------------------------------------------------- #
# 2. "Temizle" gercekten temizlemeli
# --------------------------------------------------------------------------- #

def test_hafiza_temizleme_veritabanini_da_bosaltir(tmp_path):
    """`clear_conversations()` kalici kaydi da siler."""
    h = _hafiza(tmp_path)
    h.add_conversation(NORMAL_MESAJ, "Not aldim efendim.")
    assert _ham_veritabani_metni(h).strip(), "on kosul: kayit olusmali"

    h.clear_conversations()

    assert not _ham_veritabani_metni(h).strip(), (
        "temizlemeden sonra veritabaninda kayit kaldi"
    )


def test_temizlenen_konusma_yeni_oturumda_geri_gelmez(tmp_path):
    """Codex'in deneyinin aynisi: silinen icerik sonraki prompt'a girmemeli."""
    h = _hafiza(tmp_path)
    h.add_conversation("Kirmizi arabam var", "Anladim efendim.")
    h.clear_conversations()

    # Yeni bir JarvisMemory -- yeni oturum gibi, ayni dosyalar.
    h2 = _hafiza(tmp_path)
    baglam = h2.get_context_for_prompt()

    assert "Kirmizi arabam" not in (baglam or ""), (
        "temizlenen konusma yeni oturumun prompt'una geri geldi"
    )
    assert not h2.get_recent_conversations(), "temizlenen kayit hala okunuyor"


def test_temizleme_profili_ve_olaylari_SILMEZ(tmp_path):
    """Kapsam dar olmali: "gecmisi temizle" != "her seyi unut".

    Kullanici sohbet gecmisini temizlerken dogrulanmis profil olgularini
    (adi, tercihleri) kaybetmeyi beklemez. Genis bir silme, dar bir
    silmeden daha kotu bir surprizdir.
    """
    h = _hafiza(tmp_path)
    h.profile["name"] = "Ahmet"
    h.save_profile()
    h.add_event("test", "onemli olay")
    h.add_conversation(NORMAL_MESAJ, "Not aldim.")

    h.clear_conversations()

    h2 = _hafiza(tmp_path)
    assert h2.profile.get("name") == "Ahmet", "profil silinmemeliydi"


# --------------------------------------------------------------------------- #
# 3. Ajan katmani -- "temizlendi" demek, temizlemis olmak demektir
# --------------------------------------------------------------------------- #

def test_ajanin_clear_history_metodu_kalici_depoyu_da_temizler(tmp_path):
    """`clear_history()` artik yalniz RAM'i degil, kalici kaydi da siler.

    Bu, mesajin dogru olmasi meselesi: ekranda "Gecmis temizlendi." yaziyorsa
    gecmis gercekten temizlenmis olmali.
    """
    from agent.local_agent import LocalJarvisAgent

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a.history = [{"role": "user", "content": "merhaba"}]
    a.turn_count = 1
    a.memory = _hafiza(tmp_path)
    a.memory.add_conversation(NORMAL_MESAJ, "Not aldim efendim.")

    a.clear_history()

    assert a.history == [], "RAM gecmisi temizlenmedi"
    assert not _ham_veritabani_metni(a.memory).strip(), (
        "ajan 'temizlendi' dedi ama veritabaninda kayit kaldi"
    )


def test_hafiza_yokken_clear_history_patlamaz(tmp_path):
    """Hafiza baglanmamissa temizleme yine de calismali."""
    from agent.local_agent import LocalJarvisAgent

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a.history = [{"role": "user", "content": "merhaba"}]
    a.turn_count = 1
    a.memory = None

    a.clear_history()   # istisna firlatmamali
    assert a.history == []
