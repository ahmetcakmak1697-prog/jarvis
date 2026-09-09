"""scripts/olc_llm_anatomisi.py — 10.954 ms'nin ICINI olcer.

    python scripts/olc_llm_anatomisi.py --tur 5
    python scripts/olc_llm_anatomisi.py --tur 5 --model llama3.2:latest
    python scripts/olc_llm_anatomisi.py --sinif proje_durumu

`automation/SES_GECIKMESI_20260906-2116.json` tek bir sayi biliyor:
`model_ms` p50 = 10954.0 ms. O alan `LocalJarvisAgent.chat()` cagrisinin
TAMAMINI kapsar. Icinde arac tespiti de var, prompt insasi da, Ollama da,
sonrasindaki hafiza yazimi da. Hangi parcanin ne kadar tuttugu bilinmiyor.

Bu boslugu daha once bir CIKARIM doldurdu ("darboğaz prompt isleme") ve
geri alindi: cikarim, olcum gibi sunulmustu. Bu betik cikarim yapmaz.
Her asama kendi dilimini alir.

Olculen dilimler (hepsi duvar saati, `perf_counter`)
----------------------------------------------------
    t0 -> t1   arac_tespiti_ms      `_detect_tool`
    t1 -> t2   arac_calistirma_ms   `_run_tool` (egress kapisi ICINDE)
    t2 -> t3   prompt_insa_ms       persona + proje ctx + hafiza + gecmis
    t3 -> t4   model_duvar_ms       Ollama cagrisi, istemci tarafindan
    t4 -> t5   sonrasi_ms           temizlik + gecmis + hafiza yazimi
    ------------------------------------------------------------------
               toplam_ms = t5 - t0

Ollama'nin KENDI bildirdigi sureler (`model_duvar_ms`'in icinde)
----------------------------------------------------------------
    model_yukleme_ms            `load_duration`
    model_prompt_eval_ms        `prompt_eval_duration`
    model_uretim_ms             `eval_duration`
    model_bildirilen_toplam_ms  `total_duration`
    prompt_token                `prompt_eval_count`
    uretilen_token              `eval_count`

Bu alanlar NANOSANIYE gelir; `NS_MS` ile bolunur ve donusum testle
kilitlidir. Bolme unutulursa sayi bir milyon kat buyur ve rapor sessizce
sacmalar.

Iki sozlesme
------------
* **Ad, olctugu seyi soyler.** B11'de `first_token_ms` diye bir alan vardi
  ve `prompt_eval_duration` tasiyordu -- TTFT degil. `stream=False` iken
  "ilk token" diye bir an zaten yoktur. Yanlis etiketli bir olcum, dogru
  bir olcum gibi karar verdirir.
* **Olculemeyen sey uydurulmaz.** Eksik alan `None` doner, `0` degil. `0`
  "olctum, sifirdi" demektir; `None` "olcemedim" demektir ve ortalamaya
  girmez.

NE OLCULMUYOR
-------------
* STT ve TTS. Bu betik metin girer, metin cikar. Ses hattinin ucundan uca
  suresi icin `scripts/olc_ses_gecikmesi.py` ayri durur.
* Egress kapisinin kendi payi. `_egress_kapisi` `_run_tool` ICINDE cagrilir
  ve ayrilmasi ajanin yeniden yazilmasini gerektirirdi; kapinin suresi
  `arac_calistirma_ms` icindedir.
* Ollama sunucusunun kuyruk beklemesi. `model_duvar_ms` ile
  `model_bildirilen_toplam_ms` arasindaki fark bunu KAPSAR ama ayirmaz.

**Bu betik olcer, DUZELTMEZ.** Cikan dagilim ne olursa olsun hicbir sey
optimize edilmez; optimizasyon ayri bir karttir ve Ahmet'in karari.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import time
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

__all__ = [
    "olc_tur_anatomisi", "model_olculeri", "ozetle", "rapor_yaz",
    "HEDEF_MS", "NS_MS", "OLLAMA_SECENEKLERI", "SORU_SINIFLARI",
    "OZETLENEN_ALANLAR",
]

#: CLAUDE.md 8'in soyledigi hedef. Bir kapi degil, bir olcuttur.
HEDEF_MS = 1500

#: Ollama sure alanlari NANOSANIYE gelir. Tek bolen, tek yerde.
NS_MS = 1_000_000

#: `LocalJarvisAgent._ask_ollama` ile AYNI olmali. Ajan ham yaniti atiyor
#: (yalniz `.message.content` donuyor), o yuzden sure alanlarini gorebilmek
#: icin Ollama burada dogrudan cagriliyor. Bedeli: ayar iki yerde durur.
#: `test_model_secenekleri_ajanin_kullandigiyla_ayni` ayrismayi yakalar.
#: "[Araç" = "[Araç" -- Turkce icerik escape ile yazilir (CLAUDE.md 5).
OLLAMA_SECENEKLERI: Dict[str, Any] = {
    "temperature": 0.72,
    "num_ctx": 4096,
    "num_predict": 1024,
    "stop": ["[Araç", "[System", "USER:", "JARVIS:"],
}

#: Kartin istedigi uc soru sinifi. Metinler ASCII disi karakter tasimaz ki
#: konsol/dosya kodlamasi olcumu bozmasin (CLAUDE.md 5).
#:
#: `kisa_olgusal` BILEREK arac tetiklemez: "saat kaci" `get_datetime`
#: tetikler ve o zaman olculen sey model degil arac olurdu.
SORU_SINIFLARI: Dict[str, str] = {
    "kisa_olgusal": "Bir metrede kac santimetre vardir?",
    "proje_durumu": "nerede kaldik",
    "uzun_anlatim": (
        "Bir yazilim projesinde teknik borcun nasil biriktigini, hangi "
        "belirtilerle fark edildigini ve nasil geri odendigini adim adim, "
        "ornekler vererek uzun uzun anlat."
    ),
}

#: Ozette dagilimi verilen sayisal alanlar.
OZETLENEN_ALANLAR = (
    "arac_tespiti_ms", "arac_calistirma_ms", "prompt_insa_ms",
    "model_duvar_ms", "model_yukleme_ms", "model_prompt_eval_ms",
    "model_uretim_ms", "model_bildirilen_toplam_ms", "sonrasi_ms",
    "prompt_token", "uretilen_token", "token_saniye", "cevap_uzunluk",
    "toplam_ms",
)


def _alan(kaynak: Any, ad: str) -> Any:
    """Ollama yaniti nesne de olabilir sozluk de; ikisini de oku.

    Yalniz `getattr` kullanilsa sozluk donen bir istemcide TUM alanlar
    `None` olurdu ve betik "olcemedim" diye sessizce dogru ama sessizce
    faydasiz bir rapor uretirdi.
    """
    deger = getattr(kaynak, ad, None)
    if deger is None and isinstance(kaynak, Mapping):
        deger = kaynak.get(ad)
    return deger


def _ns_ms(ns: Any) -> Optional[float]:
    """Nanosaniye -> milisaniye. Alan yoksa `None`, `0` DEGIL."""
    if ns is None:
        return None
    return round(ns / NS_MS, 1)


def _ms(bas: float, son: float) -> float:
    return round((son - bas) * 1000, 1)


def _cevap_metni(yanit: Any) -> str:
    mesaj = _alan(yanit, "message")
    return "" if mesaj is None else (_alan(mesaj, "content") or "")


def model_olculeri(yanit: Any) -> Dict[str, Any]:
    """Ollama'nin kendi bildirdigi sureleri okur; hicbirini uydurmaz."""
    uretim_ns = _alan(yanit, "eval_duration")
    token = _alan(yanit, "eval_count")

    # Sifira bolme sessiz bir sonsuzluk uretmesin: sure yoksa hiz de yok.
    token_saniye = None
    if token is not None and uretim_ns:
        token_saniye = round(token / (uretim_ns / (NS_MS * 1000)), 1)

    return {
        "model_yukleme_ms": _ns_ms(_alan(yanit, "load_duration")),
        "model_prompt_eval_ms": _ns_ms(_alan(yanit, "prompt_eval_duration")),
        "model_uretim_ms": _ns_ms(uretim_ns),
        "model_bildirilen_toplam_ms": _ns_ms(_alan(yanit, "total_duration")),
        "prompt_token": _alan(yanit, "prompt_eval_count"),
        "uretilen_token": token,
        "token_saniye": token_saniye,
    }


def olc_tur_anatomisi(
    soru: str,
    arac_tespit: Callable[[str], Optional[tuple]],
    arac_calistir: Callable[[str, dict, str], str],
    prompt_insa: Callable[[str, str], List[dict]],
    model_cagir: Callable[[List[dict]], Any],
    sonrasi: Callable[[str, str], str],
) -> Dict[str, Any]:
    """Tek turu asama asama olcer. Her parca enjekte edilebilir.

    Gercek Ollama olmadan, sahte bir model istemcisiyle kosar -- B12'deki
    `olc_tek_tur` deseni. Boylece olcum aracinin KENDISI test edilebilir.

    Asama sirasi `LocalJarvisAgent.chat()` ile aynidir: once arac tespiti
    (ciktisi kullanici mesajina girer), sonra prompt, sonra model, sonra
    temizlik. Sira degisirse olculen sey artik o tur olmaz.
    """
    t0 = time.perf_counter()

    tespit = arac_tespit(soru)
    t1 = time.perf_counter()

    if tespit:
        arac_adi, arac_arg = tespit
        arac_verisi = arac_calistir(arac_adi, arac_arg, soru)
    else:
        arac_adi, arac_verisi = None, ""
    t2 = time.perf_counter()

    mesajlar = prompt_insa(soru, arac_verisi)
    t3 = time.perf_counter()

    yanit = model_cagir(mesajlar)
    t4 = time.perf_counter()

    cevap = sonrasi(soru, _cevap_metni(yanit))
    t5 = time.perf_counter()

    tur: Dict[str, Any] = {
        "soru": soru,
        "arac": arac_adi,
        "cevap_uzunluk": len(cevap or ""),
        "arac_tespiti_ms": _ms(t0, t1),
        # Arac hic calismadiysa asama YOKTUR. `0.0` yazmak "olctum,
        # bedavaydi" demek olurdu; dogrusu "olcecek bir sey yoktu".
        "arac_calistirma_ms": _ms(t1, t2) if tespit else None,
        "prompt_insa_ms": _ms(t2, t3),
        "model_duvar_ms": _ms(t3, t4),
        "sonrasi_ms": _ms(t4, t5),
        "toplam_ms": _ms(t0, t5),
    }
    tur.update(model_olculeri(yanit))
    return tur


def _yuzdelik(dizi: List[float], p: float) -> float:
    d = sorted(dizi)
    if len(d) == 1:
        return round(d[0], 1)
    k = (len(d) - 1) * p
    alt, ust = int(k), min(int(k) + 1, len(d) - 1)
    return round(d[alt] + (d[ust] - d[alt]) * (k - alt), 1)


def ozetle(turlar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Alan alan dagilim. Tek kosu hukum degildir (A11).

    `None` tasiyan tur o alanin dagilimina GIRMEZ ve `olculen_tur` kac
    turun gercekten olculdugunu soyler -- yoksa olculmemis bir asama
    ortalamayi sifira dogru cekerdi.
    """
    if not turlar:
        return {"tur": 0}

    ozet: Dict[str, Any] = {"tur": len(turlar)}
    for alan in OZETLENEN_ALANLAR:
        d = [t[alan] for t in turlar if t.get(alan) is not None]
        if not d:
            continue
        ozet[alan] = {
            "p50": _yuzdelik(d, 0.50),
            "p95": _yuzdelik(d, 0.95),
            "min": round(min(d), 1),
            "max": round(max(d), 1),
            "ort": round(statistics.mean(d), 1),
            "olculen_tur": len(d),
        }
    return ozet


def rapor_yaz(sonuc: Dict[str, Any], hedef_dizin: Path) -> Path:
    damga = datetime.now().strftime("%Y%m%d-%H%M")
    yol = hedef_dizin / f"GECIKME_ANATOMISI_{damga}.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return yol


def _asamalar(ajan: Any, secim: Dict[str, Any]) -> Dict[str, Callable]:
    """`chat()`'in asamalarini ajanin KENDI metotlarina baglar.

    Burada hicbir mantik yeniden yazilmaz; yalniz cagrilar dilimlenir.
    Tek istisna Ollama cagrisidir: `_ask_ollama` ham yaniti atiyor ve sure
    alanlari onunla birlikte kayboluyor, o yuzden istemci dogrudan
    cagriliyor (bkz. `OLLAMA_SECENEKLERI`).
    """
    from agent.local_agent import (
        _TIER_TO_LEVEL, LOCAL_AGENT_ADDENDUM, VOICE_MODE_DIRECTIVE,
        _clean_response,
    )
    from agents.persona import build_system_prompt

    def _tespit(soru: str):
        return ajan._detect_tool(soru)

    def _calistir(ad: str, arg: dict, soru: str) -> str:
        return ajan._run_tool(ad, arg, soru)

    def _prompt(soru: str, arac_verisi: str) -> List[dict]:
        # Model secimi de prompt hazirliginin parcasi: hangi katman
        # secilirse system prompt o seviyeye gore kuruluyor.
        tier = ajan._classify(soru)
        secim["model"] = ajan._model_for_tier(tier)

        system = build_system_prompt(level=_TIER_TO_LEVEL[tier])
        system += "\n\n" + LOCAL_AGENT_ADDENDUM
        proje_ctx = ajan._proje_ctx_guncel()
        if proje_ctx:
            system += f"\n\n{proje_ctx}"
        if ajan.memory:
            ctx = ajan.memory.get_context_for_prompt()
            if ctx:
                system += f"\n\n## Hafıza\n{ctx}"
        if getattr(ajan, "voice_mode", False):
            system += "\n\n" + VOICE_MODE_DIRECTIVE

        mesajlar = [{"role": "system", "content": system}]
        gecmis = ajan.history[-16:] if len(ajan.history) > 16 else ajan.history
        mesajlar.extend(gecmis)

        if arac_verisi:
            icerik = (
                f"{soru}\n\n---\nAraştırma sonuçları "
                f"(bu verileri özümse, doğal konuş):\n"
                f"{arac_verisi}\n---\n"
            )
        else:
            icerik = soru
        mesajlar.append({"role": "user", "content": icerik})
        secim["prompt_karakter"] = sum(len(m["content"]) for m in mesajlar)
        return mesajlar

    def _model(mesajlar: List[dict]) -> Any:
        return ajan._ollama.chat(
            model=secim["model"], messages=mesajlar, stream=False,
            options=OLLAMA_SECENEKLERI,
        )

    def _sonrasi(soru: str, ham: str) -> str:
        cevap = _clean_response(ham)
        ajan.history.append({"role": "user", "content": soru})
        ajan.history.append({"role": "assistant", "content": cevap})
        if ajan.memory and len(soru) > 10:
            ajan.memory.add_conversation(soru, cevap)
            try:
                ajan.memory.auto_extract_info(soru, cevap)
            except Exception:  # noqa: BLE001 -- ajanin kendi davranisi
                pass
        if len(ajan.history) > 20:
            ajan.history = ajan.history[-16:]
        return cevap

    return {"arac_tespit": _tespit, "arac_calistir": _calistir,
            "prompt_insa": _prompt, "model_cagir": _model,
            "sonrasi": _sonrasi}


def _hafizayi_kopyala(ajan: Any) -> Optional[Path]:
    """Olcum Ahmet'in CANLI hafizasina yazmasin; kopyasina yazsin.

    `chat()` her turda `add_conversation` ve `auto_extract_info` cagirir --
    `sonrasi_ms`'in olctugu isin ta kendisi budur, atlanamaz. Ama 15 turluk
    olcum sorusu gercek hafiza veritabanina girerse sonraki her prompt'u
    kirletir. Cozum: veritabani ve profil KOPYALANIR, ajan kopyaya baglanir.
    Okuma gercek kalir (prompt boyutu gercekci olmali), yazma gecicidir.

    Kopyalanamazsa olcum durur: sessizce canli hafizaya yazmaktansa hic
    olcmemek yeglenir.
    """
    from memory.memory_manager import JarvisMemory

    gecici = Path(tempfile.mkdtemp(prefix="jarvis_olcum_"))
    kopyalar = {}
    for ad, kaynak in (("db_path", getattr(ajan.memory, "db_path", None)),
                       ("profile_path",
                        getattr(ajan.memory, "profile_path", None))):
        kaynak = Path(kaynak)
        hedef = gecici / kaynak.name
        if kaynak.exists():
            shutil.copy2(kaynak, hedef)
        kopyalar[ad] = str(hedef)

    ajan.memory = JarvisMemory(**kopyalar)
    print(f"Hafiza kopyasi: {gecici}  (canli hafizaya YAZILMIYOR)")
    return gecici


def _yazdir(ad: str, ozet: Dict[str, Any]) -> None:
    print()
    print("=" * 66)
    print(f"  {ad}  --  {ozet['tur']} tur")
    print("=" * 66)
    basliklar = (
        ("arac_tespiti_ms", "Arac tespiti"),
        ("arac_calistirma_ms", "Arac calistirma"),
        ("prompt_insa_ms", "Prompt insasi"),
        ("model_duvar_ms", "MODEL (duvar saati)"),
        ("model_yukleme_ms", "   . model yukleme"),
        ("model_prompt_eval_ms", "   . prompt degerlendirme"),
        ("model_uretim_ms", "   . URETIM"),
        ("sonrasi_ms", "Sonrasi (hafiza/kayit)"),
        ("toplam_ms", "TOPLAM"),
    )
    for alan, baslik in basliklar:
        d = ozet.get(alan)
        if not d:
            print(f"  {baslik:<26}   OLCULMEDI")
            continue
        print(f"  {baslik:<26} p50 {d['p50']:>9.1f} ms   p95 {d['p95']:>9.1f} ms")
    print("-" * 66)
    for alan, baslik in (("uretilen_token", "Uretilen token"),
                         ("prompt_token", "Prompt token"),
                         ("token_saniye", "Token/saniye")):
        d = ozet.get(alan)
        print(f"  {baslik:<26} "
              + ("OLCULMEDI" if not d else f"p50 {d['p50']:>9.1f}"))
    print("=" * 66)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="LLM turunun asama asama gecikme anatomisi")
    ap.add_argument("--tur", type=int, default=5, help="sinif basina tur")
    ap.add_argument("--sinif", action="append", choices=sorted(SORU_SINIFLARI),
                    help="yalniz bu sinif(lar); verilmezse hepsi")
    ap.add_argument("--model", default=None,
                    help="olcum icin model adi (profil dosyasi DEGISMEZ)")
    ap.add_argument("--out", default=str(_REPO / "automation"))
    a = ap.parse_args()

    from agent.local_agent import LocalJarvisAgent

    ajan = LocalJarvisAgent()
    if not ajan.ollama_available:
        print("Ollama bagli degil; olcum yapilamaz.")
        return 1
    # Olculen 10.954 ms ses yolundan geldi; ayni yonergeyle olculur.
    ajan.voice_mode = True
    gecici_hafiza = _hafizayi_kopyala(ajan)

    secim: Dict[str, Any] = {"model": a.model or ""}
    asama = _asamalar(ajan, secim)
    if a.model:
        # Model komut satirindan geldiyse `_model_for_tier`'in secimi
        # EZILIR; profil dosyasina dokunulmaz (kart sinirlari).
        gercek_prompt = asama["prompt_insa"]

        def _sabit_model(soru: str, arac_verisi: str) -> List[dict]:
            mesajlar = gercek_prompt(soru, arac_verisi)
            secim["model"] = a.model
            return mesajlar

        asama["prompt_insa"] = _sabit_model

    siniflar = a.sinif or sorted(SORU_SINIFLARI)
    kosu: Dict[str, Any] = {}
    for ad in siniflar:
        soru = SORU_SINIFLARI[ad]
        turlar: List[Dict[str, Any]] = []
        print(f"\n### {ad}: {soru[:60]}")
        # Siniflar birbirini kirletmesin: her sinif bos gecmisle baslar.
        # TUR ARASINDA silinmez -- gercek bir oturumda gecmis birikir ve
        # 10.954 ms'lik taban olcum de tam boyle alinmisti. Turden ture
        # buyuyen prompt, `prompt_token` alaninda gorunur.
        #
        # `ajan.clear_history()` KULLANILMAZ: o metot RAM'i degil kalici
        # depoyu da siler (B04) ve burada silinecek bir sey yok.
        ajan.history = []
        for i in range(a.tur):
            try:
                t = olc_tur_anatomisi(soru, **asama)
            except KeyboardInterrupt:
                print("\nKullanici durdurdu.")
                return 1
            except Exception as exc:  # noqa: BLE001
                print(f"  tur {i + 1} GECERSIZ: {type(exc).__name__}: {exc}")
                continue
            t["prompt_karakter"] = secim.get("prompt_karakter")
            t["model"] = secim.get("model")
            turlar.append(t)
            print(f"  tur {i + 1}: toplam {t['toplam_ms']:.0f} ms  "
                  f"uretim {t['model_uretim_ms']} ms  "
                  f"token {t['uretilen_token']}")
        if not turlar:
            print(f"  {ad}: hicbir tur olculemedi.")
            continue
        ozet = ozetle(turlar)
        _yazdir(ad, ozet)
        kosu[ad] = {"soru": soru, "turlar": turlar, "ozet": ozet}

    if not kosu:
        print("Hicbir sinif olculemedi.")
        return 1

    sonuc = {
        "schema_version": 1,
        "olculdu": datetime.now().isoformat(timespec="seconds"),
        "model": a.model or ajan._registry.local_main(),
        "voice_mode": True,
        "hafiza_kopyasi": str(gecici_hafiza),
        "olculmeyen": (
            "STT ve TTS bu betikte YOK. Egress kapisinin payi "
            "`arac_calistirma_ms` icindedir, ayrilmadi."
        ),
        "siniflar": kosu,
    }
    yol = rapor_yaz(sonuc, Path(a.out))
    print(f"\n  Rapor: {yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
