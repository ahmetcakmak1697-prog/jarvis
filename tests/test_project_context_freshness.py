"""B06 -- "guncel proje durumu" oturum icinde bayatlamamali.

Codex basmuhendis denetimi (2026-09-06): `LocalJarvisAgent.__init__` proje
baglamini BIR KEZ olusturuyor, `chat()` her turda ayni metni yeniden
kullaniyordu. Codex'in deneyinde yeni baglam ureticisi "STATE_AFTER"
donecek sekilde hazirlandi; bir sohbet turunda uretici **0 kez** cagrildi ve
modele "STATE_BEFORE" gonderildi.

Neden onemli: bu dogrudan PUSULA'nin ihlali. Anayasa JARVIS'in isini tek
cumleyle tanimliyor -- "repo'nun O ANKI GERCEK durumunu yansitan bir yanit;
uydurma degil, canli". Ajan acikken commit atilirsa, JARVIS eski dunyayi
anlatmaya devam ediyordu.

Ayni hatanin bir onceki surumu `agent/local_agent.py`'de proje durumunun KODA
SABIT yazilmasiydi; o da modele "her sey bekliyor" dedirtmisti (FAILURES.md).
Sabit metni canli okumaya cevirmek yetmemis -- okuma bir kez yapiliyordu.

Tazeleme PARMAK IZI ile yapilir, zamanlayiciyla degil: kaynak dosyalar
degismediyse yeniden okuma yapilmaz (her tur diski taramak bedava degil),
degistiyse ANINDA yenilenir (TTL beklemek "canli" degildir).
"""
from __future__ import annotations

import json


def _ajan():
    from agent.local_agent import LocalJarvisAgent

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a._project_ctx = ""
    a._project_ctx_imza = None
    return a


def _sahte_depo(tmp_path):
    """Yukleyicinin okudugu kaynaklari tasiyan minimal bir depo iskeleti."""
    (tmp_path / "automation").mkdir(parents=True, exist_ok=True)
    (tmp_path / "automation" / "HUMAN_NEEDED.md").write_text(
        "- [ ] [2026-09-06] [TEST-1] ilk madde\n", encoding="utf-8"
    )
    (tmp_path / "roadmap_state.json").write_text(
        json.dumps({"steps": []}), encoding="utf-8"
    )
    return tmp_path


def test_kaynak_degisince_baglam_yenilenir(tmp_path):
    """Ajan acikken dosya degisirse sonraki baglam DEGISIR."""
    kok = _sahte_depo(tmp_path)
    a = _ajan()

    once = a._proje_ctx_guncel(root=kok)
    assert "ilk madde" in once, "on kosul: ilk icerik okunmali"

    (kok / "automation" / "HUMAN_NEEDED.md").write_text(
        "- [ ] [2026-09-06] [TEST-2] IKINCI MADDE\n", encoding="utf-8"
    )

    sonra = a._proje_ctx_guncel(root=kok)
    assert "IKINCI MADDE" in sonra, (
        "kaynak degisti ama baglam eski kaldi -- B06 geri geldi"
    )
    assert "ilk madde" not in sonra


def test_kaynak_degismediyse_yeniden_okunmaz(tmp_path, monkeypatch):
    """Her tur diski taramak bedava degil; degisiklik yoksa cache kullanilir."""
    kok = _sahte_depo(tmp_path)
    a = _ajan()

    a._proje_ctx_guncel(root=kok)

    from agent.local_agent import LocalJarvisAgent

    sayac = {"n": 0}
    gercek = LocalJarvisAgent._load_project_context

    def _sayan(self, root=None):
        sayac["n"] += 1
        return gercek(self, root)

    monkeypatch.setattr(LocalJarvisAgent, "_load_project_context", _sayan)

    a._proje_ctx_guncel(root=kok)
    a._proje_ctx_guncel(root=kok)

    assert sayac["n"] == 0, (
        f"kaynak degismedigi halde {sayac['n']} kez yeniden okundu"
    )


def test_chat_her_turda_guncel_baglami_kullanir(tmp_path, monkeypatch):
    """Tam yol: `chat()` bayat metni degil, taze olani prompt'a koymali.

    Codex'in deneyinin aynisi -- fonksiyonu dogrudan cagirmak yolun kendisini
    kanitlamaz (FAILURES.md:422).
    """
    from agent.local_agent import LocalJarvisAgent
    from agents.model_registry import ModelRegistry

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a.ollama_available = True
    a.turn_count = 0
    a.history = []
    a.memory = None
    a._tools = {}
    a._registry = ModelRegistry()
    a.tool_calls_total = 0
    a.voice_mode = False
    a.available_models = ["llama3.1:latest"]
    a._project_ctx = "DURUM_ONCE"
    a._project_ctx_imza = None

    cagri_sayisi = {"n": 0}

    def _sahte_yukleyici(self, root=None):
        cagri_sayisi["n"] += 1
        return "DURUM_SONRA"

    monkeypatch.setattr(
        LocalJarvisAgent, "_load_project_context", _sahte_yukleyici
    )

    gorulen: list[str] = []
    monkeypatch.setattr(
        LocalJarvisAgent, "_ask_ollama",
        lambda self, messages, model: (
            gorulen.append(messages[0]["content"]) or "CEVAP"
        ),
    )

    a.chat("nerede kaldik")

    assert cagri_sayisi["n"] >= 1, (
        "chat() proje baglamini hic tazelemedi -- Codex'in olctugu kusur"
    )
    assert any("DURUM_SONRA" in s for s in gorulen), (
        "modele hala bayat baglam gonderildi"
    )


def test_kaynak_okunamazsa_patlamaz(tmp_path):
    """Bos/eksik bir kok istisna firlatmamali -- ses hatti durmaz."""
    a = _ajan()
    sonuc = a._proje_ctx_guncel(root=tmp_path / "olmayan_dizin")
    assert isinstance(sonuc, str)
