"""agent/cloud_llm.py — sohbet metnini uretecek DIS modele tek HTTP POST.

**Bu dosya bir tasima katmanidir ve hicbir politika karari vermez.**
Egress kapisi, "yerel kal" tespiti, arac secimi, proje baglami, persona --
hepsi `agent/local_agent.py`'de kalir. `KART_SES_YOLU_DEEPSEEK` §1'in
tarifi aynen budur: `LocalJarvisAgent.chat()` yerinde duruyor, degisen tek
sey **metni hangi modelin urettigi**.

Neden `agents/api_executor.py` kullanilmadi
-------------------------------------------
O katman async, `litellm`'e bagli ve KENDI mahremiyet/maliyet politikasini
tasiyor (`_LEVEL_PROVIDER_MAP`, `allowed_privacy`, `cost_gate`). Kartin
istedigi kapi ise `RedactionGuard`. Iki politika katmani ust uste binerse
bir turun neden disari cikmadigi anlasilmaz olur -- ve "hangi kapi kapatti"
sorusunun cevabi yoksa kapi denetlenemez. Olculmus ve calisan yol
`eval/run_turkish_quality.py:_api_ask`'in kullandigi duz OpenAI-uyumlu
POST'tur (kart §0'daki cevap o yoldan alindi); burada ayni sozlesme,
yalniz ajanin ihtiyaci kadariyla duruyor.

**Bu bir adopt-vs-build tercihidir ve raporda acikca isaretlendi.**

Yapilandirma
------------
Model adi, uc nokta ve anahtarin ADI `config/runtime_profiles.json`'dan
`ModelRegistry` uzerinden gelir (CLAUDE.md §7.1: model adi koda gomulmez).
Anahtarin DEGERI yalnizca ortamdan okunur; bu modul `.env` acmaz
(CLAUDE.md §9) -- `main.py` zaten yukluyor.

Yeniden deneme: TEK, ve butce buyumeden
---------------------------------------
Gecici bir hat hatasinda **bir kez** daha denenir (Ahmet onayi,
2026-09-11). Toplam duvar butcesi BUYUMEZ: `DEFAULT_TIMEOUT_S` bir tavandir
ve iki deneme onun icine sigdirilir (bkz. `_deneme_butceleri`). Gerekce
olculmus -- her uc turdan biri hat hatasiyla yerele dusuyordu ve o
turlarda PUSULA kiriliyordu.

Kalici hata (401/400) ve bos cevap TEKRARLANMAZ: ilki hattin degil
anahtarin, ikincisi hattin degil modelin sonucudur.

Ne YAPILMIYOR
-------------
* **Ucuncu deneme yok.** Tavan 20 s; ikiden fazlasi ya tavani deler ya da
  her denemeyi mesru cevabi kesecek kadar kisaltir.
* **Akis (stream) yok.** Ajan zaten tek parca cevap bekliyor.
"""
from __future__ import annotations

import json
import os
import socket
import time
from typing import Any, Optional

__all__ = [
    "CloudChatError",
    "DEFAULT_TIMEOUT_S",
    "cloud_chat",
    "cloud_chat_ready",
]

#: OLCULDU (2026-09-11, 21 tur): basarili uzun anlatim turu p95 **7,0 s**
#: surdu; en yavas basarili tur 7,6 s. Yani 20 s tavani mesru bir cevabi
#: kesmiyor.
#:
#: Sayi asagi cekildi cunku zaman asimi kullaniciya ZAMAN olarak oduyor:
#: ilk olcumde tavan 60 s'ti ve hat koptugunda kullanici **60 saniye**
#: bekleyip ondan sonra yerel cevabi aliyordu (olculen uctan uca 60.547 ve
#: 75.565 ms). PUSULA'nin hedefi ~1,5 s; 60 s'lik bir sessizlik cevabin
#: kendisinden daha kotudur.
#:
#: Asilirsa istisna atilir, yerele dusulur ve kullanici duyurulur (§2c).
DEFAULT_TIMEOUT_S = 20

#: Ajan `num_predict=1024` ile calisiyor (`_ask_ollama`); dis model de ayni
#: butceyle konussun ki iki taraf karsilastirlabilir kalsin.
DEFAULT_MAX_TOKENS = 1024

#: `_ask_ollama` ile AYNI. Uslup farki modelden gelsin, ayardan degil.
DEFAULT_TEMPERATURE = 0.72


# --------------------------------------------------------------------------- #
# TEK yeniden deneme — butce BOLUNUR, buyutulmez
# --------------------------------------------------------------------------- #
#
# OLCULDU (2026-09-11, `automation/SES_YOLU_DEEPSEEK_2026-09-11.md` §7a):
# 21 turun 7'si gecici ag hatasiyla yerele dustu. O turlarda cevabi llama
# verdi ve llama "nerede kaldik" sorusunu cevaplayamiyor -- yani her uc
# turdan birinde PUSULA sessizce kirildi.
#
# NAIF UYGULAMA YANLISTIR: "20 s ile dene, olmazsa 20 s ile bir daha" en
# kotu 40 saniye eder ve DEFAULT_TIMEOUT_S'in 60'tan 20'ye indirilmesiyle
# olcumle kazanilan seyi geri verir. Bu yuzden toplam duvar butcesi ayni
# kalir ve icine iki deneme SIGDIRILIR:
#
#     1. deneme    12,0 s   (toplamin %60'i)
#     geri cekilme  0,5 s
#     2. deneme     7,0 s   (toplamin %35'i)
#     ----------------------
#     en kotu      19,5 s   < 20 s tavani
#
# Sayilar olcumden: basarili uzun anlatim turu p95 7,0 s, en yavas basarili
# tur 7,6 s. 12 s'lik ilk deneme mesru hicbir cevabi kesmiyor.
#
# Geri cekilme 0,5 s: `WinError 10054` ANLIK bir kopmadir, saglayicinin
# toparlanmasini beklemek gerekmez. Olcum kosusundaki 2 s orada dogruydu
# (kullanici beklemiyordu), burada degil.
_ILK_DENEME_PAYI = 0.60
_IKINCI_DENEME_PAYI = 0.35
_GERI_CEKILME_S = 0.5

#: 5xx ve 429 gecicidir; diger 4xx (401 yanlis anahtar, 400 bozuk istek)
#: kalicidir ve tekrarlamak hem bosa gider hem hiz sinirini zorlar.
#:
#: >>> BU POLITIKA `eval/run_turkish_quality.py` ILE IKIZDIR;
#: >>> biri degisirse digeri de degismeli. <<<
#: Kopyalanmasinin sebebi: `eval/` uretim kodundan, uretim kodu `eval/`'den
#: import etmez -- ikisi de ters bagimlilik olurdu. Ortak bir modul acmak
#: spekulatif genislemedir (CLAUDE.md §2).
_GECICI_HTTP_KODLARI = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def _gecici_ag_hatasi(exc: BaseException) -> bool:
    """Bu hata yeniden denemeye deger mi?

    Ayri fonksiyon olmasinin sebebi: "hangi hata gecicidir" bir POLITIKA
    kararidir ve tek yerde durmali.

    `HTTPError` bir `URLError` ALT SINIFI oldugu icin once o ayiklanir --
    yoksa yanlis anahtar (401) da gecici sayilir ve bosuna tekrarlanir.

    >>> BU POLITIKA `eval/run_turkish_quality.py:_gecici_ag_hatasi` ILE
    >>> IKIZDIR; biri degisirse digeri de degismeli. <<<
    """
    import urllib.error

    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _GECICI_HTTP_KODLARI
    return isinstance(exc, (urllib.error.URLError, ConnectionError,
                            TimeoutError, socket.timeout))


def _deneme_butceleri(toplam: float) -> list[float]:
    """Toplam duvar butcesini denemelere boler. Toplami ASLA asmaz.

    Butce iki denemeye + geri cekilmeye sigmiyorsa tek deneme yapilir:
    yeniden deneme bir kolayliktir, tavani delmek icin gerekce degil.
    """
    if toplam <= 0:
        return [0.0]
    ilk = round(toplam * _ILK_DENEME_PAYI, 6)
    ikinci = round(toplam * _IKINCI_DENEME_PAYI, 6)
    if ilk + _GERI_CEKILME_S + ikinci > toplam:
        return [toplam]
    return [ilk, ikinci]


class CloudChatError(RuntimeError):
    """Dis modelden cevap alinamadi.

    Mesajda anahtar ASLA gecmez: bazi kutuphaneler istek basliklarini
    istisna metnine koyar, o yuzden metin yeniden kurulur.
    """


def _yapilandirma(registry: Any | None = None) -> Optional[dict[str, str]]:
    """Profil dis modeli tanimliyor mu? Tanimlamiyorsa ``None``."""
    if registry is None:
        from agents.model_registry import ModelRegistry
        registry = ModelRegistry()

    model = registry.cloud_chat_model()
    url = registry.cloud_chat_url()
    anahtar_adi = registry.cloud_chat_key_env()
    if not (model and url and anahtar_adi):
        return None
    return {"model": model, "url": url, "env": anahtar_adi}


def cloud_chat_ready(registry: Any | None = None) -> bool:
    """Dis model hem tanimli hem kullanilabilir mi?

    Anahtar yoksa bulut yolu **kapalidir** -- ajan hicbir sey denemeden
    yerelde kalir. Anahtarin kendisi okunmaz, yalnizca varligi sinanir.
    """
    yapilandirma = _yapilandirma(registry)
    if yapilandirma is None:
        return False
    return bool(os.environ.get(yapilandirma["env"], "").strip())


def _http_json(url: str, govde: bytes, basliklar: dict[str, str],
               timeout: float) -> dict[str, Any]:
    """Tek HTTP POST. Ayri fonksiyon olmasinin sebebi test edilebilirlik:
    cagrinin kendisi degistirilir, aga cikilmadan sozlesme sinanir."""
    import urllib.request

    istek = urllib.request.Request(url, data=govde, headers=basliklar,
                                   method="POST")
    with urllib.request.urlopen(istek, timeout=timeout) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def cloud_chat(
    messages: list[dict],
    *,
    registry: Any | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict[str, Any]:
    """``messages`` listesini dis modele sorar.

    Doner: ``{"text", "model", "finish_reason", "prompt_tokens",
    "completion_tokens"}``.

    Basarisiz her durumda `CloudChatError` firlatir -- **bos string
    donmez.** Sessiz bir bos cevap, cagiran tarafta "model boyle dedi"
    diye okunurdu; oysa olan sey hattin kopmasidir ve kullanici bunu
    duymali (kart §2c).
    """
    yapilandirma = _yapilandirma(registry)
    if yapilandirma is None:
        raise CloudChatError("dis model profilde tanimli degil")

    url = yapilandirma["url"]
    if not url.lower().startswith("https://"):
        # Giden yuk system prompt'un TAMAMINI icerir; duz metin bir
        # baglantidan cikmasi kabul edilemez.
        raise CloudChatError("dis uc nokta https degil, istek gonderilmedi")

    anahtar = os.environ.get(yapilandirma["env"], "").strip()
    if not anahtar:
        raise CloudChatError(
            f"{yapilandirma['env']} ortamda tanimli degil"
        )

    govde = json.dumps({
        "model": yapilandirma["model"],
        "messages": messages,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": max_tokens,
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")

    basliklar = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {anahtar}",
    }

    def _temizle(exc: BaseException) -> str:
        # Anahtar istisna metnine sizabilir (bazi kutuphaneler basliklari
        # hata mesajina koyar). Mesaj yeniden kurulur -- SON denemenin
        # hatasi da ayni temizlikten gecer.
        metin = str(exc)
        return metin.replace(anahtar, "[REDACTED]") if anahtar else metin

    butceler = _deneme_butceleri(timeout)
    for sira, butce in enumerate(butceler, start=1):
        try:
            yanit = _http_json(url, govde, basliklar, butce)
            break
        except Exception as exc:  # noqa: BLE001 - tur degil, sebep tasiyoruz
            # Son deneme ya da KALICI hata: yukari cikar. Kalici hatayi
            # tekrarlamak hem bosa gider hem hiz sinirini zorlar.
            if sira >= len(butceler) or not _gecici_ag_hatasi(exc):
                raise CloudChatError(
                    f"{type(exc).__name__}: {_temizle(exc)}"
                ) from None
            time.sleep(_GERI_CEKILME_S)

    secim = (yanit.get("choices") or [{}])[0]
    metin = ((secim.get("message") or {}).get("content") or "").strip()
    if not metin:
        raise CloudChatError("dis model bos cevap dondu")

    kullanim = yanit.get("usage") or {}
    return {
        "text": metin,
        "model": yapilandirma["model"],
        "finish_reason": secim.get("finish_reason"),
        "prompt_tokens": int(kullanim.get("prompt_tokens") or 0),
        "completion_tokens": int(kullanim.get("completion_tokens") or 0),
    }
