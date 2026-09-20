"""chat_stream AYNI veri-cikisi kapisindan gecer.

NEDEN BU TEST VAR: akis ayri bir metot olarak eklendi ve ayri metot
yazmanin en kolay yolu kapiyi baypas etmektir. `chat()` buluta cikmadan
once `_bulut_kapisi()`'na sorar -- hassas veri varsa, icerik sinifi
belirlenemiyorsa ya da kullanici "yerel kal" dediyse cikmaz (CLAUDE.md
§7). Akis bu kapiyi atlarsa, egress kontrolunde sessiz bir delik acilir
ve kimse fark etmez, cunku cevap yine gelir.

Bu dosya o deligi kilitler.
"""
from __future__ import annotations

import pytest

from agent.local_agent import LocalJarvisAgent


class _SahteAjan(LocalJarvisAgent):
    """Agir kurulumu atlayan iskelet: yalniz yonlendirme sinanir."""

    def __init__(self, bulut_acik: bool, engel: str | None):
        self._bulut_acik_mi = bulut_acik
        self._engel = engel
        self.cagrilan: list[str] = []
        self.turn_count = 0
        self.history = []
        self.memory = None

    # --- gercek sinifin kapisi, aynen kullaniliyor ---
    def _bulut_acik(self) -> bool:
        return self._bulut_acik_mi

    def _bulut_kapisi(self, user_message, messages):
        self.cagrilan.append("kapi")
        return self._engel

    # --- disari cikan iki yol ---
    def _ask_cloud_stream(self, messages):
        self.cagrilan.append("bulut")
        yield "bulut "
        yield "cevabi."

    def _ask_ollama(self, messages, model):
        self.cagrilan.append("yerel")
        return "yerel cevabi."

    # --- akisin ihtiyac duydugu, burada onemsiz olan parcalar ---
    def _mesajlari_hazirla(self, user_message):
        return "llama3.1:latest", [{"role": "user", "content": user_message}]

    def _duyur(self, metin):
        self.cagrilan.append("duyuru")


def test_kapi_izin_verirse_bulut_akar():
    a = _SahteAjan(bulut_acik=True, engel=None)
    assert "".join(a.chat_stream("selam")) == "bulut cevabi."
    assert a.cagrilan == ["kapi", "bulut"]


def test_kapi_ENGELLERSE_buluta_CIKILMAZ():
    """En onemli test: engel varsa akis yerele duser, buluta gitmez."""
    a = _SahteAjan(bulut_acik=True, engel="[model] hassas veri var")
    cikan = "".join(a.chat_stream("kart numaram 1234"))
    assert "bulut" not in a.cagrilan, "kapi engelledigi halde buluta cikildi"
    assert "yerel" in a.cagrilan
    assert cikan == "yerel cevabi."


def test_engel_kullaniciya_DUYURULUR():
    """Sessizce yerele dusmek PUSULA'nin sessizce kirilmasidir."""
    a = _SahteAjan(bulut_acik=True, engel="[model] hassas veri var")
    list(a.chat_stream("x"))
    assert "duyuru" in a.cagrilan


def test_bulut_kapaliysa_kapi_sorulmaz_yerel_calisir():
    a = _SahteAjan(bulut_acik=False, engel=None)
    assert "".join(a.chat_stream("selam")) == "yerel cevabi."
    assert a.cagrilan == ["yerel"]


def test_yerel_yol_tek_parca_verir():
    """Yerel yol henuz akmiyor; tek parca vermesi DOGRU davranis.
    Cumle tamponu tek parcayi da sorunsuz isler."""
    a = _SahteAjan(bulut_acik=False, engel=None)
    assert list(a.chat_stream("selam")) == ["yerel cevabi."]


def test_chat_imzasi_degismedi():
    """2000+ test chat()'e bagli; akis AYRI metot."""
    import inspect
    p = inspect.signature(LocalJarvisAgent.chat).parameters
    assert list(p) == ["self", "user_message"]
    assert hasattr(LocalJarvisAgent, "chat_stream")


def test_akis_bulut_hatasinda_yerele_duser():
    class Patlayan(_SahteAjan):
        def _ask_cloud_stream(self, messages):
            self.cagrilan.append("bulut")
            raise RuntimeError("hat koptu")
            yield  # pragma: no cover

    a = Patlayan(bulut_acik=True, engel=None)
    assert "".join(a.chat_stream("selam")) == "yerel cevabi."
    assert a.cagrilan == ["kapi", "bulut", "duyuru", "yerel"]


def test_akis_ORTASINDA_kopunca_yerele_DUSULMEZ():
    """Parca verildikten sonra yerele dusmek cevabi bastan aldirir ve
    kullanici ayni seyi iki kez duyar. Yarim kalmak dogru davranistir."""
    class YarimKalan(_SahteAjan):
        def _ask_cloud_stream(self, messages):
            self.cagrilan.append("bulut")
            yield "yarim"
            raise RuntimeError("ortada koptu")

    a = YarimKalan(bulut_acik=True, engel=None)
    with pytest.raises(RuntimeError):
        list(a.chat_stream("selam"))
    assert "yerel" not in a.cagrilan
