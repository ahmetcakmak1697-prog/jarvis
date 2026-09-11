"""Ses yolu dis (bulut) modele baglanirken acilan uc deligin sozlesmesi.

`KART_SES_YOLU_DEEPSEEK` §2: `LocalJarvisAgent.chat()` metni artik dis bir
saglayiciya urettirebiliyor. Kart bunun UC delik actigini soyluyor; ucu de
burada kilitli:

2a  Her sohbet turu artik bir egress ve giden sey yalniz kullanicinin
    cumlesi degil -- system prompt'un ICINDE proje baglami ve hafiza da
    var. Giden yukun TAMAMI denetlenir; hassassa tur DISARI CIKMAZ,
    yerel modele duser.
2b  "internete cikma" artik MODELI de kapsar. Kullanici yerel kalmak
    isterse metni yerel model uretir.
2c  Ag/API hatasinda yerele dusulur -- ama SESSIZ dusulmez. Sessizce
    llama'ya dusmek, PUSULA'nin sessizce yeniden kirilmasi demektir.

**Testlerin kendisi de sinandi (kart ADIM 2).** `call_count == 0` iddia
eden bir test, kapi hic kurulmamisken de yesil yanar; o zaman kusuru
degil kendi kurgusunu olcer. Bu yuzden her kapi testi once bir KONTROL
turu kosar: temiz bir tur gercekten dis modele cikiyor mu? Cikmiyorsa
kapi degil, hattin yoklugu olculur ve test kirmizi yanar.

Bu dosyadaki hicbir test AGA CIKMAZ: dis uc sahtedir ve cagrilari sayar.
"""
from __future__ import annotations

import ast
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

#: Gercek proje baglamina benzeyen, hassas HICBIR sey icermeyen blok.
_TEMIZ_CTX = (
    "## GUNCEL PROJE DURUMU\n\n"
    "### Son Commitler\n"
    "  bfb4581 olcum(terazi/etap2): yeni tanimda llama 52/64\n"
    "### Yol Haritasi Durumu\n"
    "  Tamamlanan adim: 13/14\n"
)

#: Ayni blok, icinde bir sir var. Gercek dunyada bu bir commit mesajindan,
#: `HUMAN_NEEDED` maddesinden ya da hafizadan gelebilir.
_HASSAS_CTX = _TEMIZ_CTX + "  TELEGRAM_BOT_TOKEN=123456:ABCdefGHI\n"


def _anahtar_adi() -> str:
    from agents.model_registry import ModelRegistry

    return ModelRegistry().cloud_chat_key_env()


def _tur(
    monkeypatch,
    mesaj: str,
    *,
    proje_ctx: str = _TEMIZ_CTX,
    bulut_hata: BaseException | None = None,
    bulut_cevap: str = "BULUT_CEVAP",
    gercek_bulut: bool = False,
    defter=None,
) -> dict:
    """Tek bir `chat()` turu kosar; dis uc SAHTEDIR ve cagrilari sayar.

    Doner: ``{"cevap", "bulut_cagrilari", "bildirimler"}``.

    `__new__` ile kurulur cunku gercek `__init__` Ollama'ya baglanir ve
    hafiza acar; bu dosyanin sinadigi sey ikisi de degil (repodaki mevcut
    desen -- bkz. `tests/test_pdf_branch_hijack.py`).
    """
    from agent.local_agent import LocalJarvisAgent
    from agents.model_registry import ModelRegistry

    bulut_cagrilari: list[list[dict]] = []
    bildirimler: list[str] = []

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a.ollama_available = True
    a.turn_count = 0
    a.history = []
    a.memory = None
    a._tools = {}
    a.tool_calls_total = 0
    a.voice_mode = False
    a.available_models = ["llama3.1:latest"]
    a._registry = ModelRegistry()
    a._notify = bildirimler.append
    if defter is not None:
        a._ledger = defter

    # Proje baglami testin verdigidir; diskten okunmasin. Parmak izi sabit
    # tutulur, yoksa `_proje_ctx_guncel` gercek depoyu okur.
    a._project_ctx = proje_ctx
    a._project_ctx_imza = "sabit"
    monkeypatch.setattr(
        LocalJarvisAgent, "_proje_ctx_imzasi",
        lambda self, root: "sabit", raising=False,
    )

    # Anahtar SAHTE: dis modelin "yapilandirilmis" sayilmasi icin yeterli,
    # gercek bir cagri icin degil. Gercek anahtar varsa da bununla ezilir.
    monkeypatch.setenv(_anahtar_adi(), "test-anahtari-gercek-degil")

    monkeypatch.setattr(
        LocalJarvisAgent, "_ask_ollama",
        lambda self, messages, model: "YEREL_CEVAP", raising=False,
    )

    if not gercek_bulut:
        def _sahte_bulut(self, messages):
            bulut_cagrilari.append(messages)
            if bulut_hata is not None:
                raise bulut_hata
            return bulut_cevap

        monkeypatch.setattr(
            LocalJarvisAgent, "_ask_cloud", _sahte_bulut, raising=False,
        )

    cevap = a.chat(mesaj)
    return {
        "cevap": cevap,
        "bulut_cagrilari": bulut_cagrilari,
        "bildirimler": bildirimler,
    }


# --------------------------------------------------------------------------- #
# ADIM 1 -- model adi koda gomulmez (CLAUDE.md §7.1)
# --------------------------------------------------------------------------- #

def test_bulut_modeli_ve_uc_noktasi_profilden_gelir():
    """Model adi, uc nokta ve ANAHTARIN ADI yapilandirmadan cozulur."""
    from agents.model_registry import ModelRegistry

    reg = ModelRegistry()
    assert reg.cloud_chat_model(), "cloud_chat_model rolu bos"
    assert reg.cloud_chat_url().startswith("https://"), (
        "dis uc nokta https olmali; system prompt bu baglantidan cikiyor"
    )
    assert reg.cloud_chat_key_env(), "anahtarin ADI profilde tanimli degil"


#: `tests/test_local_agent_wiring.py` ile ayni desen. Orasi yalniz
#: `local_agent.py`'yi tariyor; tasima modulu yeni bir dosya ve ayni
#: kurala tabi.
_MODEL_ADI = re.compile(
    r"\b(llama|qwen|mistral|mixtral|gemma|phi|deepseek|nemo)[\w.\-]*(:[\w.\-]+)?",
    re.IGNORECASE,
)


def test_bulut_tasima_modulunde_gomulu_model_adi_yok():
    """Yeni dosya da model adi tasimaz -- profil degisince kod degismez."""
    kaynak = _REPO / "agent" / "cloud_llm.py"
    agac = ast.parse(kaynak.read_text(encoding="utf-8"))

    docstringler: set[int] = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.Module, ast.ClassDef, ast.FunctionDef,
                              ast.AsyncFunctionDef)):
            ilk = dugum.body[0] if dugum.body else None
            if (isinstance(ilk, ast.Expr)
                    and isinstance(ilk.value, ast.Constant)
                    and isinstance(ilk.value.value, str)):
                docstringler.add(id(ilk.value))

    bulunan = [
        d.value for d in ast.walk(agac)
        if isinstance(d, ast.Constant)
        and isinstance(d.value, str)
        and id(d) not in docstringler
        and _MODEL_ADI.search(d.value)
    ]
    assert not bulunan, f"cloud_llm.py icinde gomulu model adi var: {bulunan}"


# --------------------------------------------------------------------------- #
# Suit guvenligi -- testler kazara aga cikmasin
# --------------------------------------------------------------------------- #

def test_anahtar_ortamda_yoksa_bulut_yolu_kapali(monkeypatch):
    """Anahtar yoksa hicbir sey denenmez; davranis degisiklikten oncekidir.

    OLCULDU (2026-09-11): bu koruma yokken `pytest tests` GERCEK bir
    DeepSeek cagrisi yapti ve giden yuk gercek proje baglamiydi. Kok
    neden ortamda: `agents/persona.py` ve `config.py` import edilirken
    `load_dotenv()` cagiriyor, yani `.env`'deki anahtar kabukta tanimli
    olmasa bile suit boyunca `os.environ`'a giriyor. Silme islemi tek
    noktadan, `tests/conftest.py`'de yapilir.
    """
    import os

    from agent.cloud_llm import cloud_chat_ready
    from agents.model_registry import ModelRegistry

    assert os.environ.get(_anahtar_adi()) is None, (
        "dis saglayici anahtari test ortaminda duruyor -- conftest korumasi "
        "calismiyor ve suit aga cikabilir"
    )
    assert cloud_chat_ready(ModelRegistry()) is False


# --------------------------------------------------------------------------- #
# 2a -- giden yukun tamami denetlenir
# --------------------------------------------------------------------------- #

def test_temiz_turda_metni_dis_model_uretir(monkeypatch):
    """Kapinin OLCULEBILIR olmasi icin once hattin canli oldugu gorulur."""
    sonuc = _tur(monkeypatch, "nerede kaldik")
    assert len(sonuc["bulut_cagrilari"]) == 1, "dis model hic cagrilmadi"
    assert sonuc["cevap"] == "BULUT_CEVAP"


def test_hassas_baglam_dis_saglayiciya_cikmaz(monkeypatch):
    """System prompt'un icindeki sir disari cikmaz; tur yerelde biter."""
    kontrol = _tur(monkeypatch, "nerede kaldik", proje_ctx=_TEMIZ_CTX)
    assert len(kontrol["bulut_cagrilari"]) == 1, (
        "kontrol turu dis modele hic cikmadi -- bu test kapiyi degil, "
        "hattin yoklugunu olcuyor"
    )

    hassas = _tur(monkeypatch, "nerede kaldik", proje_ctx=_HASSAS_CTX)
    assert hassas["bulut_cagrilari"] == [], (
        "hassas veri tasiyan system prompt dis saglayiciya gitti"
    )
    assert hassas["cevap"] == "YEREL_CEVAP", "cevap yerel modelden gelmedi"
    assert hassas["bildirimler"], "yerelde kalindi ama kullaniciya soylenmedi"


def test_giden_yuk_denetimi_kullanici_cumlesiyle_sinirli_degil(monkeypatch):
    """Sir yalniz system prompt'ta; kullanicinin cumlesi tertemiz.

    Yalnizca `user_message` denetleyen bir kapi bu turu disari birakir.
    """
    sonuc = _tur(monkeypatch, "nerede kaldik", proje_ctx=_HASSAS_CTX)
    assert sonuc["bulut_cagrilari"] == [], (
        "denetim yalniz kullanici mesajina bakiyor; proje baglami sizdi"
    )


def test_guard_arizasi_disari_cikmayi_kapatir(monkeypatch):
    """Denetim CALISTIRILAMAZSA da tur disari cikmaz (voice_loop.py:158).

    Codex B10 router'da bunun tersini buldu: guard hatasi yutulup dis
    cagri yine de yapiliyordu.
    """
    from agents.redaction_guard import RedactionGuard

    kontrol = _tur(monkeypatch, "nerede kaldik")
    assert len(kontrol["bulut_cagrilari"]) == 1, "kontrol turu disari cikmadi"

    def _patla(self, text):
        raise RuntimeError("guard bozuk")

    monkeypatch.setattr(RedactionGuard, "contains_sensitive_data", _patla)

    bozuk = _tur(monkeypatch, "nerede kaldik")
    assert bozuk["bulut_cagrilari"] == [], (
        "denetim patladi ama dis cagri yine de yapildi"
    )
    assert bozuk["cevap"] == "YEREL_CEVAP"
    assert bozuk["bildirimler"], "guard arizasi sessiz gecti"


# --------------------------------------------------------------------------- #
# 2b -- "yerel kal" artik modeli de kapsar
# --------------------------------------------------------------------------- #

def test_yerel_kal_talebi_modeli_de_yerelde_tutar(monkeypatch):
    """Kullanici "internete cikma" derse metni yerel model uretir.

    Cevap YINE GELIR -- reddetme yok, yalniz yerelden gelir.
    """
    kontrol = _tur(monkeypatch, "nerede kaldik")
    assert len(kontrol["bulut_cagrilari"]) == 1, "kontrol turu disari cikmadi"

    yerel = _tur(monkeypatch, "internete cikma, nerede kaldik")
    assert yerel["bulut_cagrilari"] == [], (
        "kullanici yerel kal dedi ama model yine de disari cikti"
    )
    assert yerel["cevap"] == "YEREL_CEVAP", "cevap gelmedi -- reddetme yasak"
    assert yerel["bildirimler"], "yerelde kalindi ama kullaniciya soylenmedi"


# --------------------------------------------------------------------------- #
# 2c -- geri dusme sessiz olmaz
# --------------------------------------------------------------------------- #

def test_ag_hatasinda_yerele_dusulur_ve_kullanici_bilgilendirilir(monkeypatch):
    sonuc = _tur(
        monkeypatch, "nerede kaldik",
        bulut_hata=RuntimeError("baglanti uzaktan koparildi"),
    )
    assert len(sonuc["bulut_cagrilari"]) == 1, "dis model hic denenmedi"
    assert sonuc["cevap"] == "YEREL_CEVAP", "yerele dusulmedi, tur coktu"
    assert sonuc["bildirimler"], (
        "SESSIZCE yerele dusuldu -- kart §2c'nin tam yasakladigi sey"
    )


def test_geri_dusme_bildirimi_cevaba_karismaz(monkeypatch):
    """Bildirim SESLENDIRILMEZ: cevabin icine girmez, ekranda kalir."""
    sonuc = _tur(
        monkeypatch, "nerede kaldik",
        bulut_hata=RuntimeError("baglanti uzaktan koparildi"),
    )
    assert sonuc["cevap"] == "YEREL_CEVAP", (
        "durum satiri cevabin icine karismis; hoparlorden okunurdu"
    )


def test_uc_geri_dusme_sebebi_birbirinden_ayirt_edilebilir(monkeypatch):
    """Kullanici HANGI sebeple yerelde kalindigini bilmeli."""
    hassas = _tur(monkeypatch, "nerede kaldik", proje_ctx=_HASSAS_CTX)
    yerel = _tur(monkeypatch, "internete cikma, nerede kaldik")
    ag = _tur(
        monkeypatch, "nerede kaldik",
        bulut_hata=RuntimeError("baglanti uzaktan koparildi"),
    )

    metinler = [
        " ".join(s["bildirimler"]) for s in (hassas, yerel, ag)
    ]
    assert all(metinler), f"bildirimsiz durum var: {metinler}"
    assert len(set(metinler)) == 3, (
        f"uc sebep ayni cumleyi kullaniyor: {metinler}"
    )


# --------------------------------------------------------------------------- #
# ADIM 5 -- harcama gorunur olsun (§7.0b)
# --------------------------------------------------------------------------- #

def test_bulut_cagrisi_cost_ledger_a_yazilir(monkeypatch, tmp_path):
    """Cagri sayisi VE token toplami var olan deftere yazilir.

    Yeni dosya/dizin acilmaz: `CostLedger` zaten `cost_ledger.jsonl`'e
    append ediyor (kart ADIM 5).
    """
    import agent.cloud_llm as cloud_llm
    from agents.cost_ledger import CostLedger

    def _sahte_http(url, govde, basliklar, timeout):
        assert "Authorization" in basliklar, "anahtar gonderilmiyor"
        return {
            "choices": [{"message": {"content": "BULUT_CEVAP"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 34},
        }

    monkeypatch.setattr(cloud_llm, "_http_json", _sahte_http)

    defter = CostLedger(daily_limit=0, data_root=tmp_path)
    sonuc = _tur(monkeypatch, "nerede kaldik",
                 gercek_bulut=True, defter=defter)

    assert sonuc["cevap"] == "BULUT_CEVAP"

    yol = tmp_path / "cost_ledger.jsonl"
    assert yol.exists(), "defter dosyasi yazilmadi"
    satirlar = [
        json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()
    ]
    assert len(satirlar) == 1, f"tek cagri, tek satir bekleniyordu: {satirlar}"

    kayit = satirlar[0]
    assert kayit["count"] == 1
    assert kayit["date"] == datetime.now().strftime("%Y-%m-%d")
    assert kayit["prompt_tokens"] == 1200
    assert kayit["completion_tokens"] == 34
    assert kayit["total_tokens"] == 1234

    ozet = defter.stats()
    assert ozet["today_count"] == 1
    assert ozet["total_tokens"] == 1234


def test_yerelde_kalan_tur_deftere_yazilmaz(monkeypatch, tmp_path):
    """Harcama olmayan tur harcama gibi gorunmez."""
    from agents.cost_ledger import CostLedger

    defter = CostLedger(daily_limit=0, data_root=tmp_path)
    _tur(monkeypatch, "internete cikma, nerede kaldik", defter=defter)

    yol = tmp_path / "cost_ledger.jsonl"
    assert not yol.exists() or not yol.read_text(encoding="utf-8").strip(), (
        "yerelde kalan tur deftere harcama yazdi"
    )


# --------------------------------------------------------------------------- #
# KART_BULUT_TEK_YENIDEN_DENEME -- tek yeniden deneme, butce buyumeden
# --------------------------------------------------------------------------- #
#
# Olculdu (2026-09-11): 21 turun 7'si gecici ag hatasiyla yerele dustu ve o
# turlarda cevabi llama verdi -- yani her uc turdan birinde PUSULA sessizce
# kirildi. Duzeltme tek yeniden deneme; ama naif hali ("20 s ile dene, olmazsa
# 20 s ile bir daha") dun olcumle kazanilan 60->20 indirimini geri verirdi.
#
# Bu yuzden butce BOLUNUR, buyutulmez. Asagidaki testler iki seyi birden
# kilitler: yeniden deneme VAR, ve toplam tavan AYNI.


def _bulut_ortami(monkeypatch):
    """Dis modeli "yapilandirilmis" sayan sahte ortam; aga cikilmaz."""
    from agents.model_registry import ModelRegistry

    monkeypatch.setenv(_anahtar_adi(), "test-anahtari-gercek-degil")
    return ModelRegistry()


_MESAJLAR = [
    {"role": "system", "content": "sistem"},
    {"role": "user", "content": "nerede kaldik"},
]


def _basarili_yanit(metin: str = "BULUT_CEVAP") -> dict:
    return {
        "choices": [{"message": {"content": metin}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3},
    }


def _http_401():
    import urllib.error

    return urllib.error.HTTPError(
        "https://ornek.gecersiz/chat", 401, "Unauthorized", {}, None,
    )


def test_gecici_hatadan_sonra_ikinci_deneme_cevabi_getirir(monkeypatch):
    """Birinci deneme koparsa tur SESSIZCE kaybedilmez, bir kez daha denenir."""
    import agent.cloud_llm as cloud_llm

    cagrilar: list[float] = []

    def _sahte_http(url, govde, basliklar, timeout):
        cagrilar.append(timeout)
        if len(cagrilar) == 1:
            raise ConnectionResetError("WinError 10054")
        return _basarili_yanit()

    monkeypatch.setattr(cloud_llm, "_http_json", _sahte_http)
    sonuc = cloud_llm.cloud_chat(_MESAJLAR, registry=_bulut_ortami(monkeypatch))

    assert sonuc["text"] == "BULUT_CEVAP", "ikinci deneme cevabi getirmedi"
    assert len(cagrilar) == 2, f"tam 2 deneme bekleniyordu: {len(cagrilar)}"


def test_iki_deneme_de_koparsa_ucuncu_deneme_YOK(monkeypatch):
    """Yeniden deneme TEKtir. Ucuncu deneme butceyi asardi."""
    import agent.cloud_llm as cloud_llm

    cagrilar: list[float] = []

    def _hep_kopar(url, govde, basliklar, timeout):
        cagrilar.append(timeout)
        raise ConnectionResetError("WinError 10054")

    monkeypatch.setattr(cloud_llm, "_http_json", _hep_kopar)

    with pytest.raises(cloud_llm.CloudChatError):
        cloud_llm.cloud_chat(_MESAJLAR, registry=_bulut_ortami(monkeypatch))

    assert len(cagrilar) == 2, (
        f"tam 2 deneme bekleniyordu, {len(cagrilar)} yapildi"
    )


def test_kalici_hata_TEKRARLANMAZ(monkeypatch):
    """401 yanlis anahtardir; tekrarlamak hem bosa gider hem hiz sinirini zorlar.

    `HTTPError` bir `URLError` ALT SINIFIDIR. Once o ayiklanmazsa yanlis
    anahtar da "gecici" sayilir ve bosuna tekrarlanir.
    """
    import agent.cloud_llm as cloud_llm

    cagrilar: list[float] = []

    def _yetkisiz(url, govde, basliklar, timeout):
        cagrilar.append(timeout)
        raise _http_401()

    monkeypatch.setattr(cloud_llm, "_http_json", _yetkisiz)

    with pytest.raises(cloud_llm.CloudChatError):
        cloud_llm.cloud_chat(_MESAJLAR, registry=_bulut_ortami(monkeypatch))

    assert len(cagrilar) == 1, (
        f"kalici hata tekrarlandi: {len(cagrilar)} deneme"
    )


def test_bos_cevap_TEKRARLANMAZ(monkeypatch):
    """Bos cevap hattin degil MODELIN sonucudur; tekrarlamak duzeltmez."""
    import agent.cloud_llm as cloud_llm

    cagrilar: list[float] = []

    def _bos(url, govde, basliklar, timeout):
        cagrilar.append(timeout)
        return _basarili_yanit("")

    monkeypatch.setattr(cloud_llm, "_http_json", _bos)

    with pytest.raises(cloud_llm.CloudChatError, match="bos cevap"):
        cloud_llm.cloud_chat(_MESAJLAR, registry=_bulut_ortami(monkeypatch))

    assert len(cagrilar) == 1, f"bos cevap tekrarlandi: {len(cagrilar)}"


def test_iki_denemenin_butcesi_toplam_tavani_ASMAZ(monkeypatch):
    """Kartin asil meselesi: yeniden deneme VAR ama tavan BUYUMEZ.

    Naif uygulama (20 s dene, olmazsa 20 s daha) en kotu 40 saniye eder ve
    dun olcumle kazanilan 60->20 indirimini geri verir.
    """
    import agent.cloud_llm as cloud_llm

    butceler = cloud_llm._deneme_butceleri(cloud_llm.DEFAULT_TIMEOUT_S)

    assert len(butceler) == 2, "tek yeniden deneme bekleniyordu"
    assert butceler == [12.0, 7.0], f"kartin bolusumu degismis: {butceler}"

    toplam = sum(butceler) + cloud_llm._GERI_CEKILME_S
    assert toplam <= cloud_llm.DEFAULT_TIMEOUT_S, (
        f"iki deneme toplami {toplam} s, tavan {cloud_llm.DEFAULT_TIMEOUT_S} s"
    )


def test_denemelere_gecen_zaman_asimi_bolunmus_butcedir(monkeypatch):
    """Bolusum hesapta degil, `_http_json`'a GECEN degerde gorunmeli."""
    import agent.cloud_llm as cloud_llm

    gecen: list[float] = []

    def _hep_kopar(url, govde, basliklar, timeout):
        gecen.append(timeout)
        raise ConnectionResetError("WinError 10054")

    monkeypatch.setattr(cloud_llm, "_http_json", _hep_kopar)

    with pytest.raises(cloud_llm.CloudChatError):
        cloud_llm.cloud_chat(_MESAJLAR, registry=_bulut_ortami(monkeypatch))

    assert gecen == [12.0, 7.0], (
        f"denemelere gecen zaman asimi bolunmemis: {gecen}"
    )


def test_anahtar_yeniden_deneme_yolunda_da_sizmaz(monkeypatch):
    """Redaksiyon son hata mesajinda da gecerli.

    Yeniden deneme, hata metnini SON denemeden alir. O yol da ayni
    temizlikten gecmezse anahtar istisna metniyle disari sizar.
    """
    import agent.cloud_llm as cloud_llm

    anahtar = "sk-gizli-anahtar-sizmamali"
    monkeypatch.setenv(_anahtar_adi(), anahtar)

    from agents.model_registry import ModelRegistry

    def _anahtari_sizdir(url, govde, basliklar, timeout):
        # Bazi kutuphaneler istek basliklarini hata metnine koyar.
        raise ConnectionResetError(f"baglanti koptu: {basliklar['Authorization']}")

    monkeypatch.setattr(cloud_llm, "_http_json", _anahtari_sizdir)

    with pytest.raises(cloud_llm.CloudChatError) as hata:
        cloud_llm.cloud_chat(_MESAJLAR, registry=ModelRegistry())

    assert anahtar not in str(hata.value), "anahtar hata mesajina sizdi"
    assert "[REDACTED]" in str(hata.value), "redaksiyon uygulanmadi"


def test_iki_deneme_de_koparsa_ajan_yerele_duser_ve_bildirir(monkeypatch):
    """Mevcut davranis BOZULMAZ: kullanici hala "hat koptu" diye duyar.

    `agent/local_agent.py` bu kartta DEGISMEDI; bu test onun hala dogru
    davrandigini kilitler.
    """
    import agent.cloud_llm as cloud_llm

    cagrilar: list[float] = []

    def _hep_kopar(url, govde, basliklar, timeout):
        cagrilar.append(timeout)
        raise ConnectionResetError("WinError 10054")

    monkeypatch.setattr(cloud_llm, "_http_json", _hep_kopar)

    sonuc = _tur(monkeypatch, "nerede kaldik", gercek_bulut=True)

    assert len(cagrilar) == 2, f"tam 2 deneme bekleniyordu: {len(cagrilar)}"
    assert sonuc["cevap"] == "YEREL_CEVAP", "yerele dusulmedi"
    assert sonuc["bildirimler"], "SESSIZCE yerele dusuldu"
