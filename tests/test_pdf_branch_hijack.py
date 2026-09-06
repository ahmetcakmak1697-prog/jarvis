"""B07 -- genel bir istek PDF yoluna sapmamali.

Codex basmuhendis denetimi (2026-09-06): `chat()`'in en basindaki PDF dali
"pdf, dosya, dokuman, makale, oku, analiz, incele, bak, indir" alt
dizilerinden BIRINI gorunce normal sohbeti tamamen birakiyor.

Codex'in deneyi: "Bu kodun mantigini analiz et" cumlesi sahte bagimliliklarla
**en yeni PDF'yi bul -> RAG kur -> belgeleri indeksle -> RAG sorgula**
sirasini calistirdi. Normal ajan cagrisi 0 oldu.

Dalin icinde neler atlaniyor:
  * `find_and_load_pdf()` KULLANICININ SECMEDIGI bir dosyayi aliyor --
    Desktop/Downloads/cwd icindeki en yeni PDF.
  * `JarvisRAG` kendi sabit `mistral-nemo:latest` varsayilanini kullaniyor;
    ModelRegistry devre disi (CLAUDE.md 7: "model adi koda gomulmez").
  * persona, ses yonergesi, sohbet gecmisi ve hafiza bu dalda yok.

Ayrica dal duz `.lower()` kullaniyor -- CLAUDE.md 6'nin tuzagi:
`"INCELE".lower()` birlesik noktali `i̇ncele` uretir ve "incele" ile eslesmez.
Ve alt dize aradigi icin "bak" -> "bakalim", "oku" -> "okul" yakalar.

En sinsi tarafi: bu dal `_detect_tool`'dan ONCE calisiyor. Yani `_fold_tr` ve
`keyword_present` ile ozenle kurulmus arac tespiti, ondan daha kaba bir
kontrol tarafindan atlanıyor.

**Duzeltmenin yonu (Codex):** genel analiz istegini dosya islemi saymamak.
Yanlis negatif ucuz -- kullanici "pdf oku" der ve calisir. Yanlis pozitif
pahali -- kod sorusu rastgele bir PDF'e sapiyor.
"""
from __future__ import annotations

import pytest


# --------------------------------------------------------------------------- #
# PDF yoluna SAPMAMASI gerekenler -- gunluk, mesru istekler
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    "Bu kodun mantigini analiz et",
    "Bu kodun mantığını analiz et",
    "Şu fonksiyona bir bak",
    "Bakalim ne olacak",
    "Okulda ne oldugunu anlat",
    "Projeyi incele ve yorumla",
    "Hangi dosyada bu fonksiyon var",
    "Dun ne okudum hatirliyor musun",
    "İNCELE ŞUNU",
    "Son durumu analiz eder misin",
    # A-07: `.md`/`.txt` uzantisi belge istegi degildir. Bu bir kod deposu;
    # README.md ve requirements.txt gunluk kod sorularinin konusu.
    "README.md nedir?",
    "requirements.txt nedir?",
    "CLAUDE.md dosyasinda ne yaziyor",
    # A-07: "belge" koku tek basina istek degildir -- sozluk sorusu ve
    # "belgesel" (bambaska bir kelime) buraya dusuyordu.
    "belge ne demek?",
    "belgesel oner",
    "Dun belgesel izledim",
])
def test_genel_istek_pdf_yoluna_sapmaz(mesaj):
    from agent.local_agent import _pdf_istegi_mi

    assert not _pdf_istegi_mi(mesaj), (
        f"genel istek PDF dalina sapti: {mesaj!r}"
    )


# --------------------------------------------------------------------------- #
# PDF yolunun GERCEKTEN calismasi gerekenler
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    "PDF oku",
    "pdf dosyasini yukle",
    "Şu makaleyi oku",
    "Dökümanı incele",
    "dokumani analiz et",
    "rapor.pdf dosyasini ac",
    "belgeyi oku",
    "PDF'İ İNCELE",
    # A-07: "pdf" kisa bir koktur ve kelime siniri Turkce ekleri kesiyordu.
    # Turkce sondan eklemelidir; acik bir PDF istegi kacirilmamali.
    "PDFyi oku",
    "PDFleri incele",
    "pdfyi ozetle",
    "pdf'leri tara",
])
def test_acik_belge_istegi_pdf_yolunu_tetikler(mesaj):
    from agent.local_agent import _pdf_istegi_mi

    assert _pdf_istegi_mi(mesaj), (
        f"acik belge istegi PDF dalini tetiklemedi: {mesaj!r}"
    )


# --------------------------------------------------------------------------- #
# Turkce buyuk harf tuzagi ayrica sinanir (CLAUDE.md 6)
# --------------------------------------------------------------------------- #

def test_turkce_buyuk_harf_tuzagi():
    """`"İ".lower()` birlesik nokta uretir; fold kullanilmali."""
    from agent.local_agent import _pdf_istegi_mi

    assert _pdf_istegi_mi("PDF'İ OKU") == _pdf_istegi_mi("pdf'i oku"), (
        "buyuk/kucuk harf ayni sonucu vermiyor -- duz .lower() kullanilmis"
    )
    assert _pdf_istegi_mi("DÖKÜMANI İNCELE") == _pdf_istegi_mi("dokumani incele")


# --------------------------------------------------------------------------- #
# chat() gercekten bu karara uyuyor mu -- tam yol
# --------------------------------------------------------------------------- #

def test_chat_genel_analiz_isteginde_pdf_araclarina_dokunmaz(monkeypatch):
    """Kod sorusu, dosya sistemini taramaz.

    Fonksiyonu dogrudan cagirmak yolun kendisini kanitlamaz (FAILURES.md:422);
    burada `chat()` uzerinden gecilir ve PDF/RAG cagrilarinin SIFIR oldugu
    dogrulanir.
    """
    from agent.local_agent import LocalJarvisAgent

    cagrilar: list[str] = []

    import tools.tools as tt
    monkeypatch.setattr(
        tt, "find_and_load_pdf",
        lambda *a, **k: cagrilar.append("find_and_load_pdf") or "",
        raising=False,
    )

    from agents.model_registry import ModelRegistry

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a.ollama_available = True
    a.turn_count = 0
    a.history = []
    a.memory = None
    a._project_ctx = ""
    a._tools = {}
    a._registry = ModelRegistry()
    a.tool_calls_total = 0
    a.voice_mode = False
    a.available_models = ["llama3.1:latest"]
    monkeypatch.setattr(
        LocalJarvisAgent, "_ask_ollama",
        lambda self, messages, model: "SAHTE_CEVAP", raising=False,
    )

    cevap = a.chat("Bu kodun mantigini analiz et")

    assert cagrilar == [], f"PDF araclari cagrildi: {cagrilar}"
    assert cevap == "SAHTE_CEVAP", "normal ajan yolu calismadi"
