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

Ne YAPILMIYOR
-------------
* **Yeniden deneme yok.** `eval/run_turkish_quality.py` gecici hatalarda
  3 kez deniyor cunku orada olculen sey modeldir ve kopan hat olcumu
  bozar. Burada olculen sey kullanicinin bekledigi suredir: ikinci deneme
  gecikmeyi ikiye katlar. Hata halinde yerel model devreye girer ve
  kullanici bunu duyar (kart §2c).
* **Akis (stream) yok.** Ajan zaten tek parca cevap bekliyor.
"""
from __future__ import annotations

import json
import os
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

    try:
        yanit = _http_json(url, govde, basliklar, timeout)
    except Exception as exc:  # noqa: BLE001 - tur degil, sebep tasiyoruz
        temiz = str(exc).replace(anahtar, "[REDACTED]") if anahtar else str(exc)
        raise CloudChatError(f"{type(exc).__name__}: {temiz}") from None

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
