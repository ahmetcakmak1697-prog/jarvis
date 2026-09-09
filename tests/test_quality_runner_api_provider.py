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


def test_anahtar_yoksa_ACIK_hata_verir(monkeypatch, tmp_path):
    """Sessizce yerele dusmek yerine sebebi soylenir.

    IDDIA DEGISMEDI. Degisen tek sey on kosulun ARTIK ACIK olmasi:
    K14'ten sonra `_api_ask` `.env` dosyasini da okuyor, dolayisiyla
    "anahtar yok" demek icin cwd'de `.env` OLMAMASI da gerekiyor.
    Onceden bu tesadufen dogruydu (repo'da `.env` yoktu); 2026-09-09'da
    Ahmet gercek anahtarini koyunca test onu buldu ve kirmizi yandi.
    `tmp_path` bunu tesadufe birakmiyor -- test artik hermetik.
    """
    import eval.run_turkish_quality as m

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)          # gercek .env'in gorunmedigi yer

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


def test_gecici_ag_hatasi_yeniden_denenir(monkeypatch):
    """Kopan baglanti vakayi OLDURMEMELI.

    Olculdu (2026-09-09, ilk canli frontier kosusu): 64 vakanin 15'i
    `WinError 10054 -- varolan bir baglanti uzaktaki ana bilgisayar
    tarafindan zorla kapatildi` ile bos dondu. Bos cevap puanlayicida
    dogal olarak kaliyor, yani rapor **agi olcup modele not verdi**:
    39/64 yazdi. Ayni 49 vakada gercek tablo 39'a 37'ydi.

    Tek denemeli bir olcum araci, uzun kosularda model kalitesini degil
    hat kalitesini olcer.
    """
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    monkeypatch.setattr(m.time, "sleep", lambda _s: None)   # test beklemez

    denemeler = {"n": 0}

    def _iki_kez_kopar(*_a, **_k):
        denemeler["n"] += 1
        if denemeler["n"] < 3:
            raise ConnectionResetError(
                "[WinError 10054] baglanti zorla kapatildi")
        return _sahte_yanit("efendim, buradayim")

    monkeypatch.setattr(m, "_http_json", _iki_kez_kopar)

    sonuc = m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                       system_extra="", num_predict=400)

    assert sonuc["text"] == "efendim, buradayim"
    assert denemeler["n"] == 3, "yeniden deneme yapilmadi"


def test_yeniden_deneme_SINIRLI(monkeypatch):
    """Surekli kopan hatta sonsuza kadar asilmaz; sinirli deneyip birakir."""
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    monkeypatch.setattr(m.time, "sleep", lambda _s: None)

    denemeler = {"n": 0}

    def _hep_kopar(*_a, **_k):
        denemeler["n"] += 1
        raise ConnectionResetError("[WinError 10054] koptu")

    monkeypatch.setattr(m, "_http_json", _hep_kopar)

    with pytest.raises(RuntimeError):
        m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                   system_extra="", num_predict=400)

    assert denemeler["n"] == m._API_DENEME_SAYISI
    assert 1 < denemeler["n"] <= 5, "deneme sayisi makul bir bantta olmali"


def test_kalici_hata_YENIDEN_DENENMEZ(monkeypatch):
    """Yanlis anahtar (401) gecici degildir -- tekrarlamak bosa gider.

    Ustelik 64 vaka x N deneme, saglayicinin hiz sinirina carpar ve
    gercekten gecici olan hatalari da uretir. Kalici hata bir kez denenir.
    """
    import urllib.error

    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    monkeypatch.setattr(m.time, "sleep", lambda _s: None)

    denemeler = {"n": 0}

    def _yetkisiz(*_a, **_k):
        denemeler["n"] += 1
        raise urllib.error.HTTPError(
            "https://api.deepseek.com", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(m, "_http_json", _yetkisiz)

    with pytest.raises(RuntimeError):
        m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                   system_extra="", num_predict=400)

    assert denemeler["n"] == 1, "kalici hata bosuna tekrarlandi"


def test_hiz_siniri_429_GECICI_sayilir(monkeypatch):
    """429 bir HTTPError'dir ama kalici degil -- beklenip tekrar denenir."""
    import urllib.error

    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-TEST")
    monkeypatch.setattr(m.time, "sleep", lambda _s: None)

    denemeler = {"n": 0}

    def _once_429(*_a, **_k):
        denemeler["n"] += 1
        if denemeler["n"] == 1:
            raise urllib.error.HTTPError(
                "https://api.deepseek.com", 429, "Too Many Requests", {}, None)
        return _sahte_yanit("geldi")

    monkeypatch.setattr(m, "_http_json", _once_429)

    sonuc = m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                       system_extra="", num_predict=400)

    assert sonuc["text"] == "geldi"
    assert denemeler["n"] == 2


def test_anahtar_yeniden_denemelerde_de_sizmaz(monkeypatch, capsys):
    """Yeniden deneme yolu redaksiyonu atlamamali."""
    import eval.run_turkish_quality as m

    SIR = "sk-COK-GIZLI-9931"
    monkeypatch.setenv("DEEPSEEK_API_KEY", SIR)
    monkeypatch.setattr(m.time, "sleep", lambda _s: None)

    def _sizdiran(*_a, **_k):
        raise ConnectionResetError(f"Authorization: Bearer {SIR} koptu")

    monkeypatch.setattr(m, "_http_json", _sizdiran)

    with pytest.raises(Exception) as hata:
        m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                   system_extra="", num_predict=400)

    assert SIR not in str(hata.value), "anahtar hata mesajina sizdi"
    assert SIR not in capsys.readouterr().out, "anahtar ciktiya sizdi"


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


def test_env_dosyasi_YUKLENIR(monkeypatch, tmp_path):
    """`.env` varken ek bir kabuk komutu gerekmemeli (K14).

    Olculdu (2026-09-09): betik anahtari yalniz `os.environ`'dan okuyordu
    ve `load_dotenv` cagirmiyordu (`main.py:26` cagiriyor). Ahmet `.env`i
    dogru doldurdu, betik yine "anahtar tanimli degil" dedi; cozum icin
    `.env`i PowerShell'de elle ayristirmak gerekti. Kurulum surtunmesi
    olcumun HIC yapilmamasina yol acar -- nitekim bir gun kaybedildi.
    """
    import eval.run_turkish_quality as m

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "# yorum\nDEEPSEEK_API_KEY=sk-DOSYADAN\nBOSLUK = x\n",
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(m, "_http_json", lambda *a, **k: _sahte_yanit())

    sonuc = m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                       system_extra="", num_predict=400)
    assert sonuc["text"] == "merhaba efendim"


def test_gercek_ortam_degiskeni_env_dosyasini_EZER(monkeypatch, tmp_path):
    """Kabukta tanimli anahtar dosyadakinden ustundur.

    Aksi hâlde Ahmet'in su an acik olan terminali (anahtari elle yukledigi)
    sessizce baska bir anahtara doner -- ve bunu fark etmez.
    """
    import eval.run_turkish_quality as m

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ORTAMDAN")
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=sk-DOSYADAN\n",
                                   encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    gorulen = {}

    def _yakala(url, govde, basliklar, timeout):
        gorulen["auth"] = basliklar["Authorization"]
        return _sahte_yanit()

    monkeypatch.setattr(m, "_http_json", _yakala)
    m._api_ask("deepseek/deepseek-chat", "selam", "L1",
               system_extra="", num_predict=400)

    assert gorulen["auth"] == "Bearer sk-ORTAMDAN", "dosya ortami ezdi"


def test_SUIT_gercek_env_dosyasini_SIZDIRMAZ(monkeypatch, tmp_path):
    """Testler Ahmet'in gercek anahtarini kullanamamali.

    K14 `.env` okumasini ekledi ve bunun beklenmeyen bir yan etkisi cikti:
    cwd repo koku oldugu icin `_api_ask` GERCEK `.env`i buluyor. Bir test
    `_http_json`i taklit etmeyi unutursa, Ahmet'in parasiyla gercek bir
    API cagrisi yapilir.

    Bu test sozlesmeyi kilitler: anahtar YALNIZCA ortamdan ya da cwd'deki
    `.env`ten gelir; hermetik bir cwd'de hicbir yerden anahtar bulunamaz.
    Kirmizi yanarsa cwd sizintisi geri gelmis demektir.
    """
    import eval.run_turkish_quality as m

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / ".env").exists()

    def _asla_cagrilmamali(*_a, **_k):
        raise AssertionError("anahtar bulundu ve GERCEK cagri denendi")

    monkeypatch.setattr(m, "_http_json", _asla_cagrilmamali)

    with pytest.raises(RuntimeError) as hata:
        m._api_ask("deepseek/deepseek-chat", "selam", "L1",
                   system_extra="", num_predict=400)
    assert "DEEPSEEK_API_KEY" in str(hata.value)
