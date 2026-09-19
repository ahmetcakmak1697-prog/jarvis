"""cloud_chat_stream -- bulut modelinden akan cevap. Ag'a CIKMAZ.

cloud_llm.py'nin docstring'i bugune kadar "Akis (stream) yok" diyordu ve
bu bilincliydi. Akis simdi ekleniyor cunku canli ses yolu bulut modelini
kullaniyor (chat() once _bulut_acik()'a bakiyor): tek parca bekleyen
kullanici 15-25 saniye sessizlik duyuyor.

BU TESTLERIN SINADIGI SOZLESME:
  * SSE ayristirma: "data: {...}" satirlari, "[DONE]" bitisi
  * Yeniden deneme YALNIZ ilk parca gelmeden once -- akis ortasinda
    yeniden denemek metni TEKRARLAR, ki bu sessiz bir bozulmadir
  * Anahtar hicbir cikitiya/istisnaya sizmaz
  * HTTPError (401 gibi) kalicidir, tekrar denenmez
"""
from __future__ import annotations

import io
import json

import pytest

from agent import cloud_llm

ANAHTAR = "sk-test-ASLA-SIZMAMALI-1234567890"
YAPILANDIRMA = {"url": "https://ornek.invalid/v1/chat/completions",
                "model": "deepseek-chat", "env": "TEST_BULUT_ANAHTARI"}


def _sse(*parcalar: str, bitir: bool = True) -> bytes:
    satirlar = []
    for p in parcalar:
        govde = {"choices": [{"delta": {"content": p}}]}
        satirlar.append("data: " + json.dumps(govde, ensure_ascii=False))
        satirlar.append("")
    if bitir:
        satirlar.append("data: [DONE]")
        satirlar.append("")
    return ("\n".join(satirlar) + "\n").encode("utf-8")


@pytest.fixture
def kurulum(monkeypatch):
    monkeypatch.setenv(YAPILANDIRMA["env"], ANAHTAR)
    monkeypatch.setattr(cloud_llm, "_yapilandirma", lambda registry=None: YAPILANDIRMA)


def _akis_tak(monkeypatch, cevaplar):
    """_http_akis yerine sahte: her cagride listedeki siradakini verir."""
    kayit = {"cagri": 0, "govdeler": []}

    def sahte(url, govde, basliklar, timeout):
        i = kayit["cagri"]
        kayit["cagri"] += 1
        kayit["govdeler"].append(json.loads(govde.decode("utf-8")))
        sonuc = cevaplar[min(i, len(cevaplar) - 1)]
        if isinstance(sonuc, Exception):
            raise sonuc
        return io.BytesIO(sonuc)

    monkeypatch.setattr(cloud_llm, "_http_akis", sahte)
    return kayit


def test_parcalar_sirayla_akar(kurulum, monkeypatch):
    _akis_tak(monkeypatch, [_sse("Mer", "haba ", "efendim.")])
    assert list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "selam"}])) \
        == ["Mer", "haba ", "efendim."]


def test_istek_govdesinde_stream_acik(kurulum, monkeypatch):
    kayit = _akis_tak(monkeypatch, [_sse("tamam")])
    list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "selam"}]))
    assert kayit["govdeler"][0]["stream"] is True


def test_done_sonrasi_durur(kurulum, monkeypatch):
    ham = _sse("bir", bitir=False) + b"data: [DONE]\n\n" + _sse("BU_GELMEMELI")
    _akis_tak(monkeypatch, [ham])
    assert list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}])) == ["bir"]


def test_bos_delta_atlanir(kurulum, monkeypatch):
    ham = (b'data: {"choices":[{"delta":{}}]}\n\n'
           b'data: {"choices":[{"delta":{"content":""}}]}\n\n'
           + _sse("gercek"))
    _akis_tak(monkeypatch, [ham])
    assert list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}])) == ["gercek"]


def test_bozuk_satir_akisi_oldurmez(kurulum, monkeypatch):
    ham = b"data: {bozuk json\n\n" + _sse("saglam")
    _akis_tak(monkeypatch, [ham])
    assert list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}])) == ["saglam"]


def test_ilk_parca_gelmeden_once_yeniden_denenir(kurulum, monkeypatch):
    """Ag hatasi ilk bayt gelmeden olursa tekrar denemek guvenlidir."""
    import urllib.error
    kayit = _akis_tak(monkeypatch, [urllib.error.URLError("koptu"), _sse("ikinci")])
    assert list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}])) == ["ikinci"]
    assert kayit["cagri"] == 2


def test_akis_basladiktan_sonra_yeniden_DENENMEZ(kurulum, monkeypatch):
    """EN ONEMLI TEST: parca verildikten sonra yeniden denemek metni
    tekrarlar. Yarim cevap, sessizce iki kez soylenen cevaptan iyidir."""
    import urllib.error

    def yarim_sonra_patla(url, govde, basliklar, timeout):
        class Akis(io.BytesIO):
            def __iter__(self):
                yield b'data: {"choices":[{"delta":{"content":"yarim"}}]}\n'
                raise urllib.error.URLError("ortada koptu")
        return Akis()

    monkeypatch.setattr(cloud_llm, "_http_akis", yarim_sonra_patla)
    uretec = cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}])
    assert next(uretec) == "yarim"
    with pytest.raises(cloud_llm.CloudChatError):
        next(uretec)


def test_http_hatasi_kalicidir_tekrar_denenmez(kurulum, monkeypatch):
    import urllib.error
    hata = urllib.error.HTTPError(YAPILANDIRMA["url"], 401, "Unauthorized", {}, None)
    kayit = _akis_tak(monkeypatch, [hata])
    with pytest.raises(cloud_llm.CloudChatError):
        list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}]))
    assert kayit["cagri"] == 1


def test_anahtar_hicbir_istisnaya_sizmaz(kurulum, monkeypatch):
    import urllib.error
    hata = urllib.error.HTTPError(YAPILANDIRMA["url"], 401, "Unauthorized", {}, None)
    _akis_tak(monkeypatch, [hata])
    with pytest.raises(cloud_llm.CloudChatError) as e:
        list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}]))
    assert ANAHTAR not in str(e.value)
    assert ANAHTAR not in repr(e.value)


def test_anahtar_yoksa_acikca_reddedilir(monkeypatch):
    monkeypatch.delenv(YAPILANDIRMA["env"], raising=False)
    monkeypatch.setattr(cloud_llm, "_yapilandirma", lambda registry=None: YAPILANDIRMA)
    with pytest.raises(cloud_llm.CloudChatError):
        list(cloud_llm.cloud_chat_stream([{"role": "user", "content": "x"}]))


def test_chat_imzasi_bozulmadi():
    """1700+ test cloud_chat'e bagli; akis AYRI bir fonksiyon olmali."""
    import inspect
    assert callable(cloud_llm.cloud_chat)
    assert "stream" not in inspect.signature(cloud_llm.cloud_chat).parameters
