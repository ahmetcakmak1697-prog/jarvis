"""B03 -- yerel ajanin disariya cikan araclari politikadan gecmeli.

Codex basmuhendis denetimi (2026-09-06) iki somut kusur olctu:

1. "Internete cikma, son haberler nedir?" girdisi `web_search` secti.
   Kullanicinin ACIK yasagi hicbir yerde okunmuyordu.
2. `parola=FAKE_MARKER` arama sorgusunda AYNEN kaldi; arama saglayicisina
   oldugu gibi gidecekti.

Ikisi de "koruma yazilmis ama bu yola takilmamis" sinifindan: `WebResearchPolicy`
ve `RedactionGuard` repoda var ve Telegram yolunda kullaniliyor
(`tools/telegram_agent.py:1083`), yerel ses yolunda kullanilmiyordu.

**Olculdu (2026-09-06):** mevcut politika 2. vakayi ZATEN dogru cozuyor --
`parola=...` icin `allow=False`, `mode=sensitive_blocked`, sanitize edilmis
sorgu `parola=[REDACTED]`. Yani hassas veri icin yeni mantik yazilmadi,
yalnizca var olan bilesen bu yola baglandi (CLAUDE.md 9, adopt-over-build).
Politikanin GORMEDIGI tek sey aciktan verilen "yerel kal" talimatiydi.

Kapi `_run_tool`'a konur, `_detect_tool`'a degil: sinir prompt'ta ya da niyet
tahmininde degil, YURUTME kodunda uygulanmalidir (OWASP LLM01 -- disaridan
gelen icerik model talimatina donusebilir).

Testler tam yoldan gecer: kullanici cumlesi -> `_detect_tool` -> `_run_tool`.
Fonksiyonu dogrudan cagirmak ajanin o fonksiyona giden yolunu kanitlamaz
(FAILURES.md:422).
"""
from __future__ import annotations

import pytest

#: Sentetik isaretci. Gercek bir sir DEGIL; testin "bu dizge disari cikti mi"
#: sorusunu sorabilmesi icin var.
SIR = "FAKE_AUDIT_MARKER_7719"


@pytest.fixture
def ajan():
    """Gercek LocalJarvisAgent -- Ollama yok, gercek arac sozlugu var."""
    from agent.local_agent import LocalJarvisAgent

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a._tools = a._load_tools()
    a.tool_calls_total = 0
    return a


class _Casus:
    """Gercek arac yerine gecer; cagrilip cagrilmadigini ve argumani tutar."""

    def __init__(self) -> None:
        self.cagri_sayisi = 0
        self.gelen: list[dict] = []

    def __call__(self, **kwargs):
        self.cagri_sayisi += 1
        self.gelen.append(kwargs)
        return "SAHTE_ARAMA_SONUCU"


def _casusla(ajan, arac_adi: str) -> _Casus:
    casus = _Casus()
    ajan._tools[arac_adi] = casus
    return casus


def _tam_yol(ajan, mesaj: str):
    """Kullanici cumlesinden arac ciktisina kadar; (arac_adi, cikti) doner."""
    algi = ajan._detect_tool(mesaj)
    if algi is None:
        return None, ""
    ad, kwargs = algi
    return ad, ajan._run_tool(ad, kwargs, mesaj)


# --------------------------------------------------------------------------- #
# 1. ACIK "yerel kal" talimati -- insan gecersiz kilmasi her katmandan ustun
#    (CLAUDE.md 7: "kullanici her an dur/iptal/unut/yerel-kal diyebilir")
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    "Internete cikma, son haberler nedir?",
    "İnternete çıkma, son haberler nedir?",   # Turkce harflerle -- 6 tuzagi
    "internete girme ama son haberleri soyle",
    "yerel kal, son haberler nedir",
    "disari cikma, guncel doviz kuru ne",
])
def test_acik_yerel_kal_talimati_arac_calistirmaz(ajan, mesaj):
    """Kullanici "cikma" dediyse hicbir dis cagri yapilmaz."""
    casus = _casusla(ajan, "web_search")
    ad, cikti = _tam_yol(ajan, mesaj)

    if ad is None:
        return  # hicbir arac tetiklenmediyse zaten disari cikilmadi

    assert casus.cagri_sayisi == 0, (
        f"kullanici acikca yasakladigi halde {ad} calisti: {mesaj!r}"
    )
    assert cikti, "engel sessiz olmamali -- kullaniciya sebep donmeli"


# --------------------------------------------------------------------------- #
# 2. Hassas veri -- mevcut politika zaten yakaliyor, yol ona baglanmali
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    f"sifre {SIR} hakkinda arastirma yap",
    f"parola {SIR} nedir diye ara",
    pytest.param(
        f"api key {SIR} icin guncel bilgi ver",
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "B03-EK, ACIK KUSUR: `agents/web_research_policy.py` hassas "
                "desenleri `api[_-]?key` ile ariyor -- alt cizgi ve tireyi "
                "karsiliyor, BOSLUGU karsilamiyor. Olculdu 2026-09-06: "
                "'api_key X' ve 'apikey X' bloklaniyor, 'api key X' geciyor. "
                "Bu kartta DUZELTILMEDI: politika paylasilan bir bilesen "
                "(Telegram yolu + eval/run_d2_web_policy_eval.py'nin 20 vakalik "
                "esikli takimi onu kullaniyor); sikilastirmak o olcumu oynatir "
                "ve ayri olcum ister (CLAUDE.md 3). Test SILINMEDI ki kusur "
                "gorunur kalsin: duzeltildigi an bu xfail kirmizi yanar ve "
                "isaret kaldirilir."
            ),
        ),
    ),
])
def test_hassas_sorgu_araca_ulasmaz(ajan, mesaj):
    """Hassas veri iceren sorgu arama saglayicisina gitmez.

    Iki gecerli sonuc var ve ikisi de kabul edilir:
      * hicbir arac tetiklenmedi -> zaten disari cikilmadi,
      * arac tetiklendi ama kapi engelledi -> sebep donmeli.
    Olculdu: "parola=X icin arama yap" cumlesi hicbir araci tetiklemiyor;
    testin eski hali bunu kusur saniyordu.
    """
    casus = _casusla(ajan, "web_search")
    ad, cikti = _tam_yol(ajan, mesaj)

    assert casus.cagri_sayisi == 0, f"hassas sorgu araca ulasti: {mesaj!r}"
    if ad is not None:
        assert cikti, "arac tetiklendiyse engel sessiz olmamali"


def test_sir_hicbir_arguman_icinde_disari_cikmaz(ajan):
    """Engellense bile ham sir arac argumanina sizmamali."""
    casus = _casusla(ajan, "web_search")
    _tam_yol(ajan, f"sifre {SIR} hakkinda arastirma yap")

    for kwargs in casus.gelen:
        assert SIR not in str(kwargs), (
            f"ham sir arac argumaninda gorundu: {kwargs}"
        )


# --------------------------------------------------------------------------- #
# 2b. A-04: kirpma, ORIJINALDE OLMAYAN hassas bir dizi uretebiliyor
# --------------------------------------------------------------------------- #

def test_hassas_sorgu_web_arama_yolunda_araca_ulasmaz(ajan):
    """Bosluklu `parola X` bicimi arama yolunda araca ULASMAZ.

    **Girdi degisti (2026-09-08, Ahmet onayi -- A22).** Eski hali
    `"paara rola {SIR} son haberler"` idi ve testin gucu bir KUSURA
    dayaniyordu: `_detect_tool` "ara " parcasini kelime ortasindan
    kesip hassas dizeyi KENDISI uretiyordu. K1b o kesmeyi duzeltti,
    yani eski girdi artik masum bir sorgu -- ve o haliyle disari
    cikmasi DOGRU.

    Test zayiflamadi, guclendi: artik "bug'in urettigi dize yakalaniyor
    mu" degil, "gercekten hassas girdi yakalaniyor mu" diye soruyor.
    Olculdu: `policy.decide("parola {SIR} son haberler")` ->
    `allow=False, mode=sensitive_blocked`.

    **Kapsam notu:** bu girdi ORIJINAL cumlede zaten hassas oldugu icin
    kapi ilk katmanda (B03) kapanir. A-04'un ekledigi ikinci katman --
    "orijinal temiz ama NIHAI sorgu hassas" -- asagida ayri sinaniyor.
    """
    casus = _casusla(ajan, "web_search")
    mesaj = f"parola {SIR} son haberler"

    ad, cikti = _tam_yol(ajan, mesaj)

    assert ad == "web_search", (
        f"on kosul: bu cumle web aramasi secmeli, gelen {ad}"
    )
    assert casus.cagri_sayisi == 0, (
        f"hassas sorgu araca ulasti: {casus.gelen}"
    )
    assert SIR not in str(casus.gelen), "ham isaretci arguman icinde cikti"
    assert cikti, "engel sessiz olmamali -- kullaniciya sebep donmeli"


def test_orijinal_temizken_nihai_sorgu_yine_denetlenir(ajan):
    """A-04'un kilitledigi sozlesme: NIHAI sorgu bagimsiz denetlenir.

    Politika kararini orijinal cumle verir (dogru: niyeti yargilamak
    onun isi). Ama disari cikan metin `args["query"]`'dir. Ikisi
    ayrildigi icin arada denetimsiz bir bosluk kaliyordu.

    Burada o bosluk dogrudan kurulur: orijinal cumle temiz ve politika
    ona IZIN VERIYOR (`son haberler nedir` -> allow=True), nihai sorgu
    ise hassas. Kapi kalkarsa arac cagrilir ve bu test kirmizi yanar.

    Yol `_run_tool` uzerinden gecer, `_egress_kapisi` dogrudan
    cagrilmaz: kapinin YURUTME kodunda bagli oldugu da sinanmali.
    """
    casus = _casusla(ajan, "web_search")

    cikti = ajan._run_tool(
        "web_search",
        {"query": f"parola {SIR}", "max_results": 5},
        "son haberler nedir",
    )

    assert casus.cagri_sayisi == 0, (
        f"orijinal temiz diye hassas nihai sorgu disari cikti: {casus.gelen}"
    )
    assert SIR not in str(casus.gelen), "ham isaretci arguman icinde cikti"
    assert cikti, "engel sessiz olmamali -- kullaniciya sebep donmeli"


# --------------------------------------------------------------------------- #
# 3. Mesru sorgu calismaya devam etmeli -- kapi her seyi kesmemeli
# --------------------------------------------------------------------------- #

def test_mesru_guncel_bilgi_sorgusu_hala_calisir(ajan):
    """Politika izin veriyorsa arac gercekten cagrilir."""
    casus = _casusla(ajan, "web_search")
    ad, cikti = _tam_yol(ajan, "son haberler nedir")

    assert ad == "web_search", f"beklenen web_search, gelen {ad}"
    assert casus.cagri_sayisi == 1, (
        "politika bu sorguya izin veriyor; kapi mesru cagriyi kesmemeli"
    )
    assert cikti == "SAHTE_ARAMA_SONUCU"


# --------------------------------------------------------------------------- #
# 4. deep_research de bir egress yolu -- Codex yalniz web_search'u isaretledi
# --------------------------------------------------------------------------- #

def test_deep_research_de_kapidan_gecer(ajan):
    """Ikinci disari cikan arac da denetlenir."""
    casus = _casusla(ajan, "deep_research")
    ad, cikti = _tam_yol(ajan, f"internete cikma, {SIR} konusunu derin arastir")

    if ad == "deep_research":
        assert casus.cagri_sayisi == 0, (
            "acik yasaga ragmen deep_research calisti"
        )
        assert cikti, "engel sessiz olmamali"


# --------------------------------------------------------------------------- #
# 5. Kapi YURUTMEDE, tespitte degil -- imza sozlesmesi
# --------------------------------------------------------------------------- #

def test_run_tool_orijinal_mesaji_kabul_eder(ajan):
    """`_run_tool` kullanicinin kendi cumlesini gorebilmeli.

    `_detect_tool` sorguyu olustururken anahtar kelimeleri kirpiyor; yasak
    ifadesi o kirpmada kaybolabilir. Kapinin dogru karar verebilmesi icin
    ham cumleye ihtiyaci var.

    Ucuncu parametre OPSIYONEL olmali: `tests/test_calculate_sandbox.py`
    `_run_tool`'u iki argumanla cagiriyor ve kirilmamali.
    """
    import inspect

    from agent.local_agent import LocalJarvisAgent

    imza = inspect.signature(LocalJarvisAgent._run_tool)
    parametreler = list(imza.parameters)
    assert len(parametreler) >= 4, (
        f"_run_tool orijinal mesaji almiyor: {parametreler}"
    )
    ucuncu = imza.parameters[parametreler[3]]
    assert ucuncu.default is not inspect.Parameter.empty, (
        "ucuncu parametre opsiyonel olmali -- mevcut cagiranlari kirmasin"
    )
