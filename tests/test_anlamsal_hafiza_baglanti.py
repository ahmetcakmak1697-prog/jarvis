"""Anlamsal hafizanin sohbet yoluna baglanmasi (KART_VEKTOR_HAFIZA ADIM 1/4).

Burada olculen sey aramanin KENDISI degil (o `test_anlamsal_hafiza.py`'de),
BAGLANTIDIR: blok gercekten modele giden prompt'a giriyor mu, iki yol
(`chat` ve `chat_stream`) ayni sekilde mi davraniyor, ve "unut" dendiginde
indeks de siliniyor mu.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class SahteHafiza:
    def __init__(self, blok="", temizle_sonucu=True, patla=False):
        self._blok = blok
        self._temizle_sonucu = temizle_sonucu
        self._patla = patla
        self.sorulan: list[str] = []
        self.temizle_sayisi = 0

    def prompt_blogu(self, sorgu):
        self.sorulan.append(sorgu)
        if self._patla:
            raise RuntimeError("hafiza bozuk")
        return self._blok

    def temizle(self):
        self.temizle_sayisi += 1
        if self._patla:
            raise RuntimeError("silinemedi")
        return self._temizle_sonucu


def _ajan(hafiza=None, proje_ctx="GUNCEL PROJE DURUMU"):
    with (
        patch("agent.local_agent.LocalJarvisAgent._init_ollama"),
        patch("agent.local_agent.LocalJarvisAgent._load_memory", return_value=None),
        patch("agent.local_agent.LocalJarvisAgent._load_tools", return_value={}),
        patch(
            "agent.local_agent.LocalJarvisAgent._load_project_context",
            return_value=proje_ctx,
        ),
        patch("agent.local_agent.LocalJarvisAgent._anlamsal_hafiza_kur",
              return_value=hafiza),
        patch(
            "memory.memory_manager.JarvisMemory",
            return_value=MagicMock(
                get_context_for_prompt=lambda: "",
                clear_conversations=lambda: 3,
            ),
        ),
    ):
        from agent.local_agent import LocalJarvisAgent

        ajan = LocalJarvisAgent()
        ajan.ollama_available = True
        ajan.available_models = ["llama3.1:latest"]
        return ajan


def _system_prompt(ajan, mesaj="salon klimasinin durumu ne"):
    _model, messages = ajan._mesajlari_hazirla(mesaj)
    return messages[0]["content"]


# ── prompt'a girme ───────────────────────────────────────────────────────


def test_blok_system_prompta_girer():
    hafiza = SahteHafiza(blok="## HATIRLADIKLARIN\n- [2026-09-22] Sen: kablo")
    ajan = _ajan(hafiza)

    prompt = _system_prompt(ajan)

    assert "## HATIRLADIKLARIN" in prompt
    assert "kablo" in prompt
    assert hafiza.sorulan == ["salon klimasinin durumu ne"]


def test_bos_blok_hicbir_sey_eklemez():
    """Bos baslik bile eklenmez: bos zemin, yanlis zeminden iyidir."""
    ajan = _ajan(SahteHafiza(blok=""))

    assert "HATIRLADIKLARIN" not in _system_prompt(ajan)


def test_hafiza_yoksa_sohbet_calisir():
    """chromadb kurulu degilse ya da kapatildiysa hicbir sey degismez."""
    ajan = _ajan(None)

    prompt = _system_prompt(ajan)

    assert "GUNCEL PROJE DURUMU" in prompt
    assert "HATIRLADIKLARIN" not in prompt


def test_hafiza_patlarsa_sohbet_calisir():
    """Hafiza arizasi turu dusuremez."""
    ajan = _ajan(SahteHafiza(patla=True))

    prompt = _system_prompt(ajan)

    assert "GUNCEL PROJE DURUMU" in prompt
    assert "HATIRLADIKLARIN" not in prompt


def test_akis_yolu_da_ayni_blogu_gorur():
    """`chat` ve `chat_stream` AYNI prompt'u kurar (`_mesajlari_hazirla`).

    Ikisi ayri kursaydi sesli cevapla yazili cevap farkli hatirlardi --
    sessiz ve bulunmasi zor bir fark.
    """
    hafiza = SahteHafiza(blok="## HATIRLADIKLARIN\n- [2026-09-22] Sen: kablo")
    ajan = _ajan(hafiza)
    yakalanan: list = []

    ajan._bulut_acik = lambda: False
    ajan._ask_ollama = lambda messages, model: (yakalanan.extend(messages), "ok")[1]

    list(ajan.chat_stream("salon klimasinin durumu ne"))

    assert yakalanan, "chat_stream modele hic gitmedi"
    assert "## HATIRLADIKLARIN" in yakalanan[0]["content"]


# ── unutma tutarliligi ───────────────────────────────────────────────────


def test_clear_history_indeksi_de_siler():
    """B04 yeni bir kapidan geri gelmemeli: SQLite silinip indeks kalsaydi
    'unut' denen konusma aramayla prompt'a geri girerdi."""
    hafiza = SahteHafiza()
    ajan = _ajan(hafiza)

    ajan.clear_history()

    assert hafiza.temizle_sayisi == 1


def test_indeks_silinemezse_kullanici_uyarilir():
    """Yarim temizlik SESSIZ gecmez."""
    hafiza = SahteHafiza(temizle_sonucu=False)
    ajan = _ajan(hafiza)
    basilan: list[str] = []

    with patch("agent.local_agent.console.print", side_effect=basilan.append):
        ajan.clear_history()

    assert any("anlamsal indeks temizlenemedi" in str(s) for s in basilan), basilan


def test_indeks_silme_patlarsa_temizlik_cokmez():
    hafiza = SahteHafiza(patla=True)
    ajan = _ajan(hafiza)
    basilan: list[str] = []

    with patch("agent.local_agent.console.print", side_effect=basilan.append):
        ajan.clear_history()

    assert any("silinemedi" in str(s) for s in basilan), basilan


# ── kacis kapisi ─────────────────────────────────────────────────────────


def test_env_bayragi_kapatir(monkeypatch):
    """`JARVIS_ANLAMSAL_HAFIZA=0` yolu tamamen kapatir."""
    from agent.local_agent import LocalJarvisAgent

    monkeypatch.setenv("JARVIS_ANLAMSAL_HAFIZA", "0")
    bos = object.__new__(LocalJarvisAgent)

    assert bos._anlamsal_hafiza_kur() is None
