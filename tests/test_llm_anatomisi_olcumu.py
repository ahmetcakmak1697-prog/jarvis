"""Gecikmenin anatomisi -- 10.954 ms'nin ICI olculuyor mu?

`automation/SES_GECIKMESI_20260906-2116.json` tek bir sayi biliyor:
`model_ms` p50 = 10954.0. O alan `ajan.chat()` cagrisinin TAMAMINI kapsar --
arac tespiti, prompt insasi, Ollama ve sonrasindaki hafiza yazimi hep ayni
sayinin icinde. Hangi parcanin ne kadar tuttugu bilinmiyor.

Daha once bu boslugu "darboğaz prompt isleme" diye bir CIKARIM doldurdu ve
geri alindi. Bu dosya cikarimin yerine olcumu koyar: her asama kendi
dilimini alir, hicbiri komsusunun suresini ustlenmez.

Iki sozlesme ozellikle korunur:

* **Ad, olctugu seyi soyler.** B11'de `first_token_ms` diye bir alan vardi
  ve Ollama'nin `prompt_eval_duration` degerini tasiyordu -- TTFT degil.
  Yanlis etiketli bir olcum, dogru bir olcum gibi karar verdirir.
* **Olculemeyen sey uydurulmaz.** Eksik alan `None` doner, `0` degil. `0`
  "olctum, sifirdi" demektir; `None` "olcemedim" demektir. Ikisi ayni
  ortalamaya giremez.

Donanim enjekte edilebilir: gercek Ollama olmadan, sahte bir model
istemcisiyle kosar (B12'deki `olc_tek_tur` deseni).
"""
from __future__ import annotations

import time
from types import SimpleNamespace

#: Ollama sure alanlarini NANOSANIYE dondurur. Testler bu carpani acikca
#: kullanir ki donusum bir kez kilitlensin.
NS = 1_000_000_000


def _yanit(**alanlar):
    """Ollama `ChatResponse` benzeri sahte yanit; yalniz VERILEN alanlar var.

    Verilmeyen alan gercekten YOK -- `getattr` None dondurur. Boylece
    "eksik alan None doner" sozlesmesi gercek bir eksiklikle sinanir.
    """
    alanlar.setdefault("message", SimpleNamespace(content="cevap efendim"))
    return SimpleNamespace(**alanlar)


def _gecikmeli(sn: float, doner=None):
    def _f(*_a, **_k):
        time.sleep(sn)
        return doner
    return _f


def _tur(**kw):
    """Tek turu varsayilan sahte asamalarla olcer; test yalniz ilgilendigini verir."""
    from scripts.olc_llm_anatomisi import olc_tur_anatomisi

    varsayilan = {
        "soru": "nerede kaldik",
        "arac_tespit": lambda _s: None,
        "arac_calistir": lambda _ad, _arg, _s: "",
        "prompt_insa": lambda s, _v: [{"role": "user", "content": s}],
        "model_cagir": lambda _m: _yanit(),
        "sonrasi": lambda _s, ham: ham,
    }
    varsayilan.update(kw)
    return olc_tur_anatomisi(**varsayilan)


# --------------------------------------------------------------------------- #
# 1. Nanosaniye -> milisaniye. Ollama ns dondurur; bolme unutulursa sayi
#    bir milyon kat buyur ve rapor sessizce sacmalar.
# --------------------------------------------------------------------------- #

def test_nanosaniye_milisaniyeye_cevriliyor():
    from scripts.olc_llm_anatomisi import model_olculeri

    o = model_olculeri(_yanit(
        prompt_eval_duration=350 * NS // 1000,   # 350 ms
        eval_duration=9 * NS,                    # 9000 ms
        load_duration=NS // 2,                   # 500 ms
        total_duration=10 * NS,                  # 10000 ms
    ))

    assert o["model_prompt_eval_ms"] == 350.0, o
    assert o["model_uretim_ms"] == 9000.0, o
    assert o["model_yukleme_ms"] == 500.0, o
    assert o["model_bildirilen_toplam_ms"] == 10000.0, o


def test_token_sayilari_sure_gibi_cevrilmez():
    """`eval_count` bir SAYIDIR; ns bolmesi ona uygulanamaz."""
    from scripts.olc_llm_anatomisi import model_olculeri

    o = model_olculeri(_yanit(eval_count=412, prompt_eval_count=1875))

    assert o["uretilen_token"] == 412
    assert o["prompt_token"] == 1875


def test_token_saniye_uretim_suresinden_hesaplanir():
    """Kartin sordugu turev sayi: model saniyede kac token uretiyor?"""
    from scripts.olc_llm_anatomisi import model_olculeri

    o = model_olculeri(_yanit(eval_count=200, eval_duration=4 * NS))

    assert o["token_saniye"] == 50.0, o


# --------------------------------------------------------------------------- #
# 2. Olculemeyen sey uydurulmaz. `0` bir olcumdur, `None` olcumsuzluktur.
# --------------------------------------------------------------------------- #

def test_eksik_alan_None_doner_sifir_degil():
    from scripts.olc_llm_anatomisi import model_olculeri

    o = model_olculeri(_yanit())  # hicbir sure alani yok

    for alan in ("model_prompt_eval_ms", "model_uretim_ms",
                 "model_yukleme_ms", "uretilen_token", "token_saniye"):
        assert o[alan] is None, f"{alan} uydurulmus: {o[alan]!r}"
        assert o[alan] != 0, f"{alan} olculmedigi halde sifir yazilmis"


def test_uretim_suresi_sifirken_token_saniye_uydurulmaz():
    """Sifira bolme sessiz bir sonsuzluk uretmez, `None` uretir."""
    from scripts.olc_llm_anatomisi import model_olculeri

    o = model_olculeri(_yanit(eval_count=200, eval_duration=0))

    assert o["token_saniye"] is None


def test_arac_calismadiginda_calistirma_dilimi_None():
    """Hic calismayan asama sifir ms surmez -- olculmemistir."""
    t = _tur(arac_tespit=lambda _s: None)

    assert t["arac"] is None
    assert t["arac_calistirma_ms"] is None, (
        "arac calismadi; 0 ms yazmak 'olctum, bedavaydi' demektir"
    )
    assert t["arac_tespiti_ms"] is not None, "tespit CALISTI, olculmeli"


# --------------------------------------------------------------------------- #
# 3. Dilimler ust uste binmez: parcalarin toplami turu ASMAZ, ve turun
#    kayda deger bir parcasi atfedilmemis kalmaz.
# --------------------------------------------------------------------------- #

def test_bilesenlerin_toplami_toplam_ms_i_asmaz():
    t = _tur(
        arac_tespit=_gecikmeli(0.02, ("web_search", {"query": "x"})),
        arac_calistir=_gecikmeli(0.03, "arac verisi"),
        prompt_insa=_gecikmeli(0.04, [{"role": "user", "content": "s"}]),
        model_cagir=_gecikmeli(0.10, _yanit()),
        sonrasi=_gecikmeli(0.02, "temiz cevap"),
    )

    parcalar = ("arac_tespiti_ms", "arac_calistirma_ms", "prompt_insa_ms",
                "model_duvar_ms", "sonrasi_ms")
    toplam_parca = sum(t[a] for a in parcalar)

    assert toplam_parca <= t["toplam_ms"] + 1.0, (
        f"dilimler ust uste biniyor: {toplam_parca} > {t['toplam_ms']}"
    )
    assert toplam_parca >= t["toplam_ms"] - 5.0, (
        f"turun {t['toplam_ms'] - toplam_parca:.1f} ms'i hicbir dilime "
        "atfedilmemis -- eksik asama var"
    )


def test_her_gecikme_kendi_diliminde_gorunur():
    """Komsu dilimin suresini ustlenen bir alan, yanlis yeri suclar."""
    t = _tur(
        arac_tespit=_gecikmeli(0.01, None),
        prompt_insa=_gecikmeli(0.05, [{"role": "user", "content": "s"}]),
        model_cagir=_gecikmeli(0.12, _yanit()),
        sonrasi=_gecikmeli(0.02, "temiz"),
    )

    assert 5 <= t["arac_tespiti_ms"] < 40, t["arac_tespiti_ms"]
    assert 40 <= t["prompt_insa_ms"] < 100, t["prompt_insa_ms"]
    assert 100 <= t["model_duvar_ms"] < 190, t["model_duvar_ms"]
    assert 10 <= t["sonrasi_ms"] < 60, t["sonrasi_ms"]


def test_ollama_dilimleri_model_duvar_suresini_asmaz():
    """Ollama'nin kendi bildirdigi sureler, bizim olctugumuz duvara sigar.

    Sigmiyorsa ya birim cevrimi yanlistir ya da yanlis alan okunmustur.
    """
    t = _tur(model_cagir=_gecikmeli(0.15, _yanit(
        load_duration=NS // 100,           # 10 ms
        prompt_eval_duration=NS // 50,     # 20 ms
        eval_duration=NS // 20,            # 50 ms
        total_duration=NS // 12,           # ~83 ms
    )))

    icerik = (t["model_yukleme_ms"] + t["model_prompt_eval_ms"]
              + t["model_uretim_ms"])
    assert icerik <= t["model_duvar_ms"], (
        f"bildirilen {icerik} ms > olculen duvar {t['model_duvar_ms']} ms"
    )
    assert t["model_bildirilen_toplam_ms"] <= t["model_duvar_ms"]


# --------------------------------------------------------------------------- #
# 4. Uctan uca: gercek Ollama olmadan, sahte istemciyle.
# --------------------------------------------------------------------------- #

def test_sahte_istemciyle_uctan_uca_olcum_yapilir():
    gorulen = {}

    def _prompt(soru, arac_verisi):
        gorulen["arac_verisi"] = arac_verisi
        return [{"role": "system", "content": "persona"},
                {"role": "user", "content": soru}]

    def _model(messages):
        gorulen["mesaj_sayisi"] = len(messages)
        time.sleep(0.01)  # tur suresi saat cozunurlugune sigmasin
        return _yanit(
            message=SimpleNamespace(content="  Burada kaldik efendim.  "),
            prompt_eval_duration=NS // 4,
            eval_duration=2 * NS,
            eval_count=180,
            prompt_eval_count=1450,
        )

    t = _tur(
        soru="nerede kaldik",
        arac_tespit=lambda _s: ("get_datetime", {}),
        arac_calistir=lambda _ad, _arg, _s: "2026-09-09",
        prompt_insa=_prompt,
        model_cagir=_model,
        sonrasi=lambda _s, ham: ham.strip(),
    )

    assert gorulen["arac_verisi"] == "2026-09-09", "arac ciktisi prompt'a gitmedi"
    assert gorulen["mesaj_sayisi"] == 2
    assert t["arac"] == "get_datetime"
    assert t["arac_calistirma_ms"] is not None
    assert t["model_prompt_eval_ms"] == 250.0
    assert t["model_uretim_ms"] == 2000.0
    assert t["uretilen_token"] == 180
    assert t["prompt_token"] == 1450
    assert t["token_saniye"] == 90.0
    assert t["cevap_uzunluk"] == len("Burada kaldik efendim.")
    assert t["toplam_ms"] > 0


# --------------------------------------------------------------------------- #
# 5. Ad sozlesmesi -- B11/B12 dersi.
# --------------------------------------------------------------------------- #

def test_hicbir_alan_ilk_token_iddiasinda_bulunmaz():
    """`prompt_eval_duration` TTFT DEGILDIR; oyle adlandirilamaz."""
    t = _tur(model_cagir=lambda _m: _yanit(prompt_eval_duration=NS // 4))

    for ad in t:
        assert "first_token" not in ad and "ilk_token" not in ad, (
            f"alan adi ilk-token iddiasinda: {ad}"
        )
    assert "model_prompt_eval_ms" in t, (
        "prompt degerlendirme suresi kendi adiyla raporlanmali"
    )


def test_model_secenekleri_ajanin_kullandigiyla_ayni():
    """Olcum, ajanin GERCEKTEN kullandigi ayarla yapilmali.

    `_ask_ollama` ham yaniti atar (yalniz `.message.content` doner), bu
    yuzden sure alanlarini gorebilmek icin olcum Ollama'yi kendisi cagirir.
    Bedeli: ayarlar iki yerde durur. Ayrisirlarsa rapor BASKA bir kurulumu
    olcer ve bunu kimse fark etmez -- B11'in dersi tam buydu.
    """
    import inspect

    from agent.local_agent import LocalJarvisAgent
    from scripts.olc_llm_anatomisi import OLLAMA_SECENEKLERI

    kaynak = inspect.getsource(LocalJarvisAgent._ask_ollama)

    for ad, deger in OLLAMA_SECENEKLERI.items():
        if isinstance(deger, list):
            for oge in deger:
                assert oge in kaynak, f"`stop` dizisi ayrismis: {oge!r} yok"
        else:
            assert f'"{ad}": {deger}' in kaynak, (
                f"olcum {ad}={deger} kullaniyor ama ajan baskasini kullaniyor"
            )


# --------------------------------------------------------------------------- #
# 6. Ozet -- tek kosu hukum degildir (A11).
# --------------------------------------------------------------------------- #

def test_ozet_p50_ve_dagilim_verir():
    from scripts.olc_llm_anatomisi import ozetle

    turlar = [{"toplam_ms": float(v), "model_uretim_ms": 100.0 * i}
              for i, v in enumerate((800, 900, 1000, 1100, 9000), start=1)]
    o = ozetle(turlar)

    assert o["tur"] == 5
    assert o["toplam_ms"]["p50"] == 1000.0
    assert o["toplam_ms"]["max"] == 9000.0
    assert o["model_uretim_ms"]["p50"] == 300.0


def test_ozet_olculmemis_alani_ortalamaya_katmaz():
    """`None` tasiyan turlar o alanin dagilimini KIRLETMEZ."""
    from scripts.olc_llm_anatomisi import ozetle

    o = ozetle([{"toplam_ms": 100.0, "arac_calistirma_ms": None},
                {"toplam_ms": 200.0, "arac_calistirma_ms": 40.0}])

    assert o["arac_calistirma_ms"]["ort"] == 40.0, (
        "olculmemis tur ortalamaya 0 olarak girmis"
    )
    assert o["arac_calistirma_ms"]["olculen_tur"] == 1


def test_bos_kosu_patlamaz():
    from scripts.olc_llm_anatomisi import ozetle

    assert ozetle([])["tur"] == 0
