"""Akan cevap da geçmişe YAZILMALI (2026-09-23'te ölçülerek bulundu).

Canlı bir oturumda 34 tur konuşuldu ve `memory/jarvis_memory.db`'ye
**sıfır** kayıt düştü. Sebep: `main.py` akış açıkken `chat_stream()`
kullanıyor, ama kaydı yalnız `_akisa_ver()` (yani `chat()`) yapıyordu.

Sonucu şuydu: akış modunda JARVIS hiçbir şeyi hatırlamıyordu — anlamsal
indeks bir yana, `self.history`'deki son-8-tur penceresi bile boş
kalıyordu. Her tur, ilk turmuş gibi başlıyordu.

Bu sessiz bir kusurdu: cevaplar geliyordu, ekran normaldi, hiçbir hata
basılmıyordu. Yalnız hafıza yoktu.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _ajan():
    hafiza = MagicMock()
    hafiza.get_context_for_prompt.return_value = ""
    hafiza.add_conversation = MagicMock()
    hafiza.auto_extract_info = MagicMock()

    with (
        patch("agent.local_agent.LocalJarvisAgent._init_ollama"),
        patch("agent.local_agent.LocalJarvisAgent._load_memory", return_value=None),
        patch("agent.local_agent.LocalJarvisAgent._load_tools", return_value={}),
        patch("agent.local_agent.LocalJarvisAgent._load_project_context",
              return_value=""),
        patch("agent.local_agent.LocalJarvisAgent._anlamsal_hafiza_kur",
              return_value=None),
        patch("memory.memory_manager.JarvisMemory", return_value=hafiza),
    ):
        from agent.local_agent import LocalJarvisAgent

        ajan = LocalJarvisAgent()
        ajan.ollama_available = True
        ajan.available_models = ["llama3.1:latest"]
        ajan._bulut_acik = lambda: False
        return ajan, hafiza


SORU = "Yedek kartlari kirmizi koltugun altina koydum"


def test_akan_cevap_oturum_gecmisine_yazilir():
    """Akış modunda son-8-tur penceresi de boş kalıyordu."""
    ajan, _ = _ajan()
    ajan._ask_ollama = lambda messages, model: "Not aldim efendim."

    list(ajan.chat_stream(SORU))

    assert len(ajan.history) == 2, ajan.history
    assert ajan.history[0] == {"role": "user", "content": SORU}
    assert ajan.history[1]["role"] == "assistant"
    assert "Not aldim" in ajan.history[1]["content"]


def test_akan_cevap_kalici_depoya_yazilir():
    """Yazılmazsa anlamsal indeks hiçbir zaman malzeme bulamaz."""
    ajan, hafiza = _ajan()
    ajan._ask_ollama = lambda messages, model: "Not aldim efendim."

    list(ajan.chat_stream(SORU))

    hafiza.add_conversation.assert_called_once()
    cagri = hafiza.add_conversation.call_args[0]
    assert cagri[0] == SORU
    assert "Not aldim" in cagri[1]


def test_akan_cevap_chat_ile_ayni_sekilde_temizlenir():
    """İki yol aynı metni saklamalı; yoksa geçmiş yola göre değişirdi."""
    ajan, _ = _ajan()
    ajan._ask_ollama = lambda messages, model: "[Araç: web] Cevap burada."

    list(ajan.chat_stream(SORU))

    assert "[Araç" not in ajan.history[1]["content"]


def test_bos_cevap_kaydedilmez():
    """Model hiçbir şey vermediyse saklanacak bir tur da yok."""
    ajan, hafiza = _ajan()
    ajan._ask_ollama = lambda messages, model: ""

    list(ajan.chat_stream(SORU))

    assert ajan.history == []
    hafiza.add_conversation.assert_not_called()


def test_yarim_kalan_akis_gorulen_kadariyla_kaydedilir():
    """Kullanıcı ekranda bir şey gördüyse o tur yaşanmıştır.

    Yarıda kopan bir cevabı tamamen atmak, kullanıcının gördüğü şeyi
    hafızadan silmek olurdu — sonraki turda JARVIS söylediğini bilmez.
    """
    ajan, hafiza = _ajan()

    def yarim(messages, model):
        raise AssertionError("yerel yola dusmemeliydi")

    def kopan(messages):
        yield "Kirmizi koltugun "
        raise RuntimeError("baglanti koptu")

    ajan._bulut_acik = lambda: True
    ajan._bulut_kapisi = lambda mesaj, messages: None
    ajan._ask_cloud_stream = kopan
    ajan._ask_ollama = yarim

    try:
        list(ajan.chat_stream(SORU))
    except RuntimeError:
        pass

    assert ajan.history, "yarim cevap tamamen kayboldu"
    assert "Kirmizi koltugun" in ajan.history[1]["content"]
    hafiza.add_conversation.assert_called_once()


def test_kisa_mesaj_kalici_depoya_yazilmaz():
    """`chat()` ile aynı eşik: 10 karakterden kısa mesaj diske gitmez."""
    ajan, hafiza = _ajan()
    ajan._ask_ollama = lambda messages, model: "Tamam efendim."

    list(ajan.chat_stream("selam"))

    hafiza.add_conversation.assert_not_called()
    assert len(ajan.history) == 2, "oturum gecmisine yine de girmeli"
