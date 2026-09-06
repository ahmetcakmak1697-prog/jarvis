"""A-01 (BLOCKER) -- basarisiz seslendirme "basarili tam olcum" sayilmamali.

Codex sahte bir `ConnectionError("FAKE_NETWORK_DROP")` enjekte etti; hic ses
uretilmedigi halde tur gecerli tam olcum olarak kaydedildi:
`{"exit_code": 0, "mode": "tam", "reported_turns": 1, "error_visible": false}`

Uc sebep birlesiyor ve ucu de burada sinaniyor:

1. `VoiceIO.say()` istisnayi BILEREK yutar -- o katmanin sozlesmesi "ses asla
   tek yol degildir" ve DEGISMEZ. Hata olcum tarafinda yakalanmali.
2. `build_default_voice_io(enabled=True)` cagrisina `notify` verilmiyordu,
   yani VoiceIO'nun hata bildirimi varsayilan no-op'a gidiyordu.
3. Kurulum istisna firlatmadan `enabled=False` bir VoiceIO dondurse bile
   betik `mod="tam"` yaziyordu.

Testler gercek `VoiceIO` kullanir -- sahte olan yalnizca konusmaci ve ajan.
Sahte bir VoiceIO ile test etmek, betigin gercek VoiceIO'ya nasil bagladigini
(ozellikle `notify`'i) kanitlamazdi.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


class _SahteRegistry:
    def local_main(self) -> str:
        return "sahte-model:test"


class _SahteAjan:
    def __init__(self) -> None:
        self.ollama_available = True
        self.voice_mode = False
        self._registry = _SahteRegistry()

    def chat(self, mesaj: str) -> str:
        return "Burada kaldik efendim."


class _KopanSpeaker:
    """Ag koptu: `speak` istisna firlatir. `is_local` ile B05 kapisi disarida."""

    is_local = True

    def __init__(self) -> None:
        self.cagri = 0

    def speak(self, metin: str):
        self.cagri += 1
        raise ConnectionError("FAKE_NETWORK_DROP")


class _CalisanSpeaker:
    is_local = True

    def __init__(self) -> None:
        self.cagri = 0

    def speak(self, metin: str):
        self.cagri += 1
        return SimpleNamespace(ok=True, warning="")


def _kur(monkeypatch, tmp_path, speaker, ses_acik: bool = True):
    """main()'i sahte ajan + GERCEK VoiceIO ile kosmaya hazirlar."""
    import agent.local_agent as la
    import voice.voice_loop as vl

    monkeypatch.setattr(la, "LocalJarvisAgent", _SahteAjan)

    def _sahte_build(keyboard=None, notify=None, enabled=True, **_kw):
        return vl.VoiceIO(
            speaker=speaker,
            keyboard=lambda p: "nerede kaldik",
            notify=notify,
            enabled=ses_acik,
        )

    monkeypatch.setattr(vl, "build_default_voice_io", _sahte_build)
    monkeypatch.setattr(
        "sys.argv",
        ["olc_ses_gecikmesi.py", "--tur", "1", "--out", str(tmp_path)],
    )


def _raporlar(tmp_path):
    return list(tmp_path.glob("SES_GECIKMESI_*.json"))


# ─── 1. Kopan TTS gecerli olcum degildir ────────────────


def test_kopan_tts_gecerli_olcum_sayilmaz(tmp_path, monkeypatch, capsys):
    """Hic ses uretilmediyse tur sayilmaz, betik basarili donmez."""
    from scripts.olc_ses_gecikmesi import main

    speaker = _KopanSpeaker()
    _kur(monkeypatch, tmp_path, speaker)

    rc = main()
    capsys.readouterr()

    assert speaker.cagri == 1, "seslendirme hic denenmemis -- senaryo kurulmamis"
    assert rc != 0, "hicbir ses uretilmedigi halde betik basarili dondu"
    assert not _raporlar(tmp_path), "gecersiz tur icin gecerli rapor yazildi"


def test_kopan_tts_hatasi_GORUNUR(tmp_path, monkeypatch, capsys):
    """`notify` bagli olmali: VoiceIO'nun hatasi kullaniciya ulasmali.

    Bu, `build_default_voice_io(..., notify=...)` baglantisinin testi. Bagli
    degilse VoiceIO hatayi varsayilan no-op'a yazar ve olcum sessizce
    "basarili" olur -- Codex'in `error_visible: false` bulgusu tam buydu.
    """
    from scripts.olc_ses_gecikmesi import main

    _kur(monkeypatch, tmp_path, _KopanSpeaker())

    main()
    cikti = capsys.readouterr().out

    assert "FAKE_NETWORK_DROP" in cikti, (
        f"seslendirme hatasi hicbir yerde gorunmuyor:\n{cikti[-600:]}"
    )


# ─── 2. Kurulum sessizce kapali donerse "tam" yazilmaz ──


def test_ses_kapali_donerse_tam_yazilmaz(tmp_path, monkeypatch, capsys):
    """`enabled=False` VoiceIO istisna firlatmaz; yine de tam mod degildir."""
    from scripts.olc_ses_gecikmesi import main

    _kur(monkeypatch, tmp_path, _CalisanSpeaker(), ses_acik=False)

    rc = main()
    capsys.readouterr()

    assert rc == 0, "kuru moda dusmek bir hata degil; olcum surmeli"
    raporlar = _raporlar(tmp_path)
    assert len(raporlar) == 1
    veri = json.loads(raporlar[0].read_text(encoding="utf-8"))
    assert veri["mod"] != "tam", (
        "ses katmani kapaliyken 'tam' etiketi yazildi -- yanlis etiketli "
        "olcum, dogru olcum gibi karar verdirir"
    )


# ─── 3. Asiri duzeltme kontrolu: calisan ses hala "tam" ─


def test_calisan_tts_tam_mod_ve_ses_kaniti_yazar(tmp_path, monkeypatch, capsys):
    """Gercekten seslendirilen bir tur tam olcumdur ve kaniti raporda durur."""
    from scripts.olc_ses_gecikmesi import main

    speaker = _CalisanSpeaker()
    _kur(monkeypatch, tmp_path, speaker)

    rc = main()
    capsys.readouterr()

    assert rc == 0
    assert speaker.cagri == 1
    raporlar = _raporlar(tmp_path)
    assert len(raporlar) == 1
    veri = json.loads(raporlar[0].read_text(encoding="utf-8"))
    assert veri["mod"] == "tam"
    assert len(veri["turlar"]) == 1
    assert veri["turlar"][0]["ses_kaniti"] is True, (
        "basarili turda ilk ses olayinin kaniti yok"
    )


# ─── 4. Birim: kanitsiz tur reddedilir ──────────────────


def test_ses_bekleniyorken_kanitsiz_tur_reddedilir():
    """`ses_bekleniyor=True` iken seslendirme kaniti yoksa tur gecersizdir."""
    from scripts.olc_ses_gecikmesi import OlcumBasarisiz, olc_tek_tur

    with pytest.raises(OlcumBasarisiz):
        olc_tek_tur(
            soru="soru",
            dinle=None,
            sor=lambda m: "cevap",
            seslendir=lambda c: False,
            ses_bekleniyor=True,
        )


def test_kuru_modda_kanit_beklenmez():
    """Kuru mod bilerek sessizdir; orada kanit istemek olcumu bosa cikarir."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur("soru", None, lambda m: "cevap", lambda c: None)

    assert t["ses_kaniti"] is False
    assert t["toplam_ms"] >= 0
