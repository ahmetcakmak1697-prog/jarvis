"""Kalite takimi dis saglayiciyi da olcebilmeli (frontier kiyasi).

Neden: 2026-09-06'da yerel tarafin rakami olculdu (llama3.1 49/64, kuru mod
p50 10 954 ms) ama bulut tarafinin rakami YOK. Tek tarafli bir olcumle
"yerel mi bulut mu" karari verilemez.

Bu modul HTTP CAGRISI YAPMAZ. Test edilen sey cagrinin kendisi degil,
cagriyi saran sozlesme: anahtarin nereden okundugu, hata yolunun ne
dondurdugu, ve olcum alanlarinin ayni adlari tasidigi. Gercek cagri
`--saglayici` bayragiyla Ahmet tarafindan calistirilir.

**Anahtar hicbir yere yazilmaz.** Ne loga, ne rapora, ne hata mesajina.
Testler bunu da dogrular.
"""
from __future__ import annotations

import json

import pytest


def _sahte_yanit(icerik: str = "merhaba efendim", token: int = 12):
    """OpenAI-uyumlu bir sohbet yaniti (DeepSeek bu bicimi kullanir)."""
    return {
        "choices": [{"message": {"content": icerik}}],
        "usage": {"completion_tokens": token, "prompt_tokens": 40},
    }


def test_api_cagrisi_kosucunun_alan_sozlesmesini_tutar(monkeypatch):
    """Donen sozluk `_ollama_ask` ile AYNI alanlari tasimali.

    Yoksa `run_suite` iki saglayici icin farkli davranir ve kiyas anlamsiz
    olur -- ayni terazi olmasinin sarti bu.
    """
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST-ANAHTAR")
    monkeypatch.setattr(m, "_http_json", lambda *a, **k: _sahte_yanit())

    sonuc = m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                       system_extra="", num_predict=400)

    for alan in ("text", "raw_tps", "prompt_eval_ms", "total_s", "done_reason"):
        assert alan in sonuc, f"alan sozlesmesi bozuk: {alan} yok"
    assert sonuc["text"] == "merhaba efendim"


def test_anahtar_yoksa_ACIK_hata_verir(monkeypatch):
    """Sessizce yerele dusmek yerine sebebi soylenir."""
    import eval.run_turkish_quality as m

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as hata:
        m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                   system_extra="", num_predict=400)

    assert "DEEPSEEK_API_KEY" in str(hata.value), (
        "hangi degiskenin eksik oldugu soylenmeli"
    )


def test_anahtar_hicbir_ciktida_gorunmez(monkeypatch, capsys):
    """Sir ne loga, ne hata mesajina, ne rapora sizmaz."""
    import eval.run_turkish_quality as m

    SIR = "sk-COK-GIZLI-ANAHTAR-9931"
    monkeypatch.setenv("DEEPSEEK_API_KEY", SIR)

    def _patlayan(*_a, **_k):
        raise ConnectionError("baglanti koptu")

    monkeypatch.setattr(m, "_http_json", _patlayan)

    with pytest.raises(Exception) as hata:
        m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                   system_extra="", num_predict=400)

    assert SIR not in str(hata.value), "anahtar hata mesajina sizdi"
    assert SIR not in capsys.readouterr().out, "anahtar ciktiya sizdi"


def test_prompt_eval_ms_uydurulmaz(monkeypatch):
    """Saglayici bu olcumu vermiyorsa None kalir, 0 YAZILMAZ.

    B11'in dersi: bilinmeyen olcume sayi yazmak, yanlis etiketli olcum
    kadar zararlidir -- 0 ms "cok hizli" gibi okunur.
    """
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    monkeypatch.setattr(m, "_http_json", lambda *a, **k: _sahte_yanit())

    sonuc = m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                       system_extra="", num_predict=400)

    assert sonuc["prompt_eval_ms"] is None, (
        "olculmeyen alan uydurulmus"
    )


def test_zemin_metni_sistem_prompt_una_eklenir(monkeypatch):
    """`system_extra` (hafiza zemini) kaybolmamali -- yoksa geri cagirma
    vakalari yerel ile ayni kosulda olculmez."""
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    gorulen = {}

    def _yakala(url, govde, basliklar, timeout):
        gorulen["govde"] = json.loads(govde.decode("utf-8"))
        return _sahte_yanit()

    monkeypatch.setattr(m, "_http_json", _yakala)
    m._api_ask("deepseek/deepseek-chat", "esimin adi ne?", "L2",
               system_extra="Esi: Dilara", num_predict=400)

    sistem = gorulen["govde"]["messages"][0]["content"]
    assert "Dilara" in sistem, "zemin metni sistem prompt'una girmedi"


def test_num_predict_saglayiciya_gecer(monkeypatch):
    """Butce ayni olmali; yoksa longform vakalari farkli kosulda olculur."""
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    gorulen = {}

    def _yakala(url, govde, basliklar, timeout):
        gorulen["govde"] = json.loads(govde.decode("utf-8"))
        return _sahte_yanit()

    monkeypatch.setattr(m, "_http_json", _yakala)
    m._api_ask("deepseek/deepseek-chat", "anlat", "L3",
               system_extra="", num_predict=1200)

    assert gorulen["govde"]["max_tokens"] == 1200
