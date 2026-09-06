"""scripts/olc_ses_gecikmesi.py — PUSULA'nin ucuncu sartini olcer (B12).

    python scripts/olc_ses_gecikmesi.py --tur 5
    python scripts/olc_ses_gecikmesi.py --tur 5 --soru "nerede kaldik"
    python scripts/olc_ses_gecikmesi.py --kuru        # mikrofonsuz, yalniz model+TTS

CLAUDE.md 8 hedefi uc sart tasir: Turkce sesli, repo'nun gercek durumu,
**~1,5 saniye**. Ilk ikisi calisiyor; ucuncusu 2026-09-06 itibariyle HIC
OLCULMEDI (Codex denetimi B12).

Neden mevcut sayilar yetmiyor: kalite kosucusu `prompt_eval_ms` uretir --
Ollama'nin prompt degerlendirme suresi. `stream=False` kullanildigi icin
orada "ilk token" diye bir an yoktur. Ve o olcum STT'yi, sentezi ve
oynatmayi hic gormez. 1,5 saniye bunlarin TOPLAMIDIR.

**Bu betik olcer, DUZELTMEZ.** Cikan sayi kotu bile olsa hicbir sey
degistirilmez; once gercek zaman cizelgesi bilinmeli (Codex'in kendi
tavsiyesi). Optimizasyon ayri bir karttir ve Ahmet'in karari.

Olculen dilimler
----------------
    t0  konusma bitti           (VAD karari / kuru modda: baslangic)
    t1  STT metni hazir         -> stt_ms
    t2  model cevabi tamam      -> model_ms
    t3  sentez dosyasi hazir    -> sentez_ms
    t4  ilk ses duyuldu         -> oynatma_ms
    ------------------------------------------------
        toplam = t4 - t0        -> HEDEF: <= 1500 ms

Rapor p50 ve p95 verir; tek kosu hukum degildir (A11 dersi: ayni model ayni
puanlayicida bile kosular arasi oynuyor).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

__all__ = [
    "olc_tek_tur", "ozetle", "rapor_yaz", "HEDEF_MS",
    "OlcumBasarisiz", "SesOlcumu",
]

#: CLAUDE.md 8'in soyledigi hedef. Bir kapi DEGIL, bir olcuttur: hangi
#: istatistik icin gecerli oldugu (p50 mi p95 mi) Ahmet'in urun kararidir
#: (Codex B12).
HEDEF_MS = 1500


class OlcumBasarisiz(RuntimeError):
    """Tur olculmedi. Gecerli olcum sayilmaz, ortalamaya girmez (A-01).

    Bir olcum hatti, olctugu sey olmadiginda sessizce basarili raporlayamaz;
    boyle bir hat, hat olmamasindan kotudur.
    """


class SesOlcumu:
    """`VoiceIO.say()` etrafinda ince bir KANIT toplayici (A-01).

    `say()` istisnayi bilerek yutar ve hicbir sey dondurmez -- o katmanin
    sozlesmesi "ses asla tek yol degildir" ve DOGRUDUR, degismez. Bu yuzden
    basari/basarisizlik olcum tarafinda anlasilir. Uc kaynak birlikte
    okunur, hepsi VoiceIO'nun ACIK arayuzu:

    * `vio.enabled` -- kurulum sessizce kapali donmus olabilir;
    * `speech_text(...)` -- bos metin hic seslendirilmez (VoiceIO'nun
      cagirdigi islevin ta kendisi cagrilir, esik kopyalanmaz);
    * `notify` bildirimleri -- hata varsa VoiceIO buradan haber verir.

    Hicbir bildirim gelmemesi, konusmacinin `speak()` cagrisinin kendi
    sozlesmesine gore basarili dondugu anlamina gelir; ilk ses olayinin
    kaniti budur.
    """

    def __init__(self, vio: Any, uyarilar: List[str]) -> None:
        self._vio = vio
        self._uyarilar = uyarilar

    def __call__(self, metin: Optional[str]) -> bool:
        from voice.voice_loop import speech_text

        if not getattr(self._vio, "enabled", False):
            self._uyarilar.append("[olcum] ses katmani kapali; seslendirme yok")
            return False

        if not speech_text(metin):
            self._uyarilar.append("[olcum] seslendirilecek metin yok")
            return False

        onceki = len(self._uyarilar)
        self._vio.say(metin)
        return len(self._uyarilar) == onceki


def olc_tek_tur(
    soru: str,
    dinle: Optional[Callable[[], str]],
    sor: Callable[[str], str],
    seslendir: Callable[[str], Any],
    ses_bekleniyor: bool = False,
) -> Dict[str, Any]:
    """Tek turu dilim dilim olcer. Enjekte edilebilir -- test edilebilsin.

    `dinle` None ise kuru mod: STT atlanir ve `soru` dogrudan kullanilir.
    Boylece mikrofon olmayan bir makinede model+sentez dilimleri yine olculur.

    `seslendir` gercekten ses uretildiyse dogru bir deger dondurur. Kuru modda
    ses beklenmez; `ses_bekleniyor=True` iken kanit yoksa tur GECERSIZDIR ve
    `OlcumBasarisiz` firlatilir (A-01) -- olculmeyen bir tur ortalamayi
    kirletemez.
    """
    t0 = time.perf_counter()

    if dinle is not None:
        metin = dinle()
        t1 = time.perf_counter()
    else:
        metin = soru
        t1 = t0

    cevap = sor(metin)
    t2 = time.perf_counter()

    ses_kaniti = bool(seslendir(cevap))
    t3 = time.perf_counter()

    if ses_bekleniyor and not ses_kaniti:
        raise OlcumBasarisiz(
            "seslendirme kaniti yok -- bu tur gecerli olcum degil"
        )

    ms = lambda a, b: round((b - a) * 1000, 1)  # noqa: E731
    return {
        "soru": metin,
        "cevap_uzunluk": len(cevap or ""),
        "ses_kaniti": ses_kaniti,
        "stt_ms": ms(t0, t1),
        "model_ms": ms(t1, t2),
        "ses_ms": ms(t2, t3),
        "toplam_ms": ms(t0, t3),
    }


def ozetle(turlar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """p50/p95 ozet. Tek kosu hukum degildir; dagilim raporlanir."""
    if not turlar:
        return {"tur": 0}

    def yuzdelik(dizi: List[float], p: float) -> float:
        d = sorted(dizi)
        if len(d) == 1:
            return round(d[0], 1)
        k = (len(d) - 1) * p
        alt, ust = int(k), min(int(k) + 1, len(d) - 1)
        return round(d[alt] + (d[ust] - d[alt]) * (k - alt), 1)

    ozet: Dict[str, Any] = {"tur": len(turlar)}
    for alan in ("stt_ms", "model_ms", "ses_ms", "toplam_ms"):
        d = [t[alan] for t in turlar if t.get(alan) is not None]
        if not d:
            continue
        ozet[alan] = {
            "p50": yuzdelik(d, 0.50),
            "p95": yuzdelik(d, 0.95),
            "min": round(min(d), 1),
            "max": round(max(d), 1),
            "ort": round(statistics.mean(d), 1),
        }

    toplam = ozet.get("toplam_ms", {})
    ozet["hedef_ms"] = HEDEF_MS
    ozet["p50_hedefte_mi"] = (
        toplam.get("p50", float("inf")) <= HEDEF_MS if toplam else None
    )
    ozet["p95_hedefte_mi"] = (
        toplam.get("p95", float("inf")) <= HEDEF_MS if toplam else None
    )
    return ozet


def rapor_yaz(sonuc: Dict[str, Any], hedef_dizin: Path) -> Path:
    damga = datetime.now().strftime("%Y%m%d-%H%M")
    yol = hedef_dizin / f"SES_GECIKMESI_{damga}.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return yol


def _yazdir(ozet: Dict[str, Any]) -> None:
    print()
    print("=" * 58)
    print(f"  SES HATTI GECIKMESI — {ozet['tur']} tur")
    print("=" * 58)
    basliklar = {"stt_ms": "STT (konusma -> metin)",
                 "model_ms": "Model (metin -> cevap)",
                 "ses_ms": "Sentez + oynatma",
                 "toplam_ms": "TOPLAM"}
    for alan, baslik in basliklar.items():
        d = ozet.get(alan)
        if not d:
            continue
        ayrac = "-" * 58 if alan == "toplam_ms" else ""
        if ayrac:
            print(ayrac)
        print(f"  {baslik:<26} p50 {d['p50']:>8.1f} ms   p95 {d['p95']:>8.1f} ms")
    print("-" * 58)
    hedef = ozet.get("hedef_ms")
    for etiket, anahtar in (("p50", "p50_hedefte_mi"), ("p95", "p95_hedefte_mi")):
        durum = ozet.get(anahtar)
        if durum is None:
            continue
        isaret = "HEDEFTE" if durum else "HEDEF DISI"
        print(f"  {etiket} <= {hedef} ms ? {isaret}")
    print("=" * 58)
    print("  Not: hangi istatistigin kabul siniri oldugu Ahmet'in urun")
    print("  kararidir. Bu betik olcer, hukum vermez.")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Ses hatti uctan uca gecikme olcumu")
    ap.add_argument("--tur", type=int, default=5, help="kac tur olculecek")
    ap.add_argument("--soru", default="nerede kaldik",
                    help="kuru modda sorulacak metin")
    ap.add_argument("--kuru", action="store_true",
                    help="mikrofonsuz: STT atlanir, model+sentez olculur")
    ap.add_argument("--out", default=str(_REPO / "automation"))
    a = ap.parse_args()

    from agent.local_agent import LocalJarvisAgent

    ajan = LocalJarvisAgent()
    if not ajan.ollama_available:
        print("Ollama bagli degil; olcum yapilamaz.")
        return 1
    ajan.voice_mode = True

    def _sessiz(_metin: str) -> bool:
        """Kuru modda oynatma yok; dilim sifir kalir, uydurulmaz."""
        return False

    dinle = None
    seslendir: Callable[[str], Any] = _sessiz
    ses_aktif = False
    #: VoiceIO hatalarini buraya yazar. Bagli olmazsa hata varsayilan
    #: no-op'a gider ve olcum sessizce "basarili" olur (A-01).
    uyarilar: List[str] = []

    if not a.kuru:
        try:
            from voice.voice_loop import build_default_voice_io
            vio = build_default_voice_io(enabled=True, notify=uyarilar.append)
            # Kurulum istisna FIRLATMADAN kapali bir VoiceIO dondurebilir;
            # o durumda hicbir ses cikmaz ama betik eskiden "tam" yaziyordu.
            if not getattr(vio, "enabled", False):
                raise OlcumBasarisiz("ses katmani kapali dondu")
            dinle = lambda: vio.prompt("Konusun efendim: ")  # noqa: E731
            seslendir = SesOlcumu(vio, uyarilar)
            ses_aktif = True
        except Exception as exc:  # noqa: BLE001
            print(f"Ses katmani kurulamadi ({exc}); kuru moda dusuluyor.")

    if not ses_aktif:
        print("KURU MOD — STT ve oynatma OLCULMUYOR.")
        print("Bu sayilar 1,5 saniye hedefini kanitlamaz; alt sinirdir.")

    turlar: List[Dict[str, Any]] = []
    basarisiz = 0
    for i in range(a.tur):
        print(f"\n--- tur {i + 1}/{a.tur} ---")
        onceki_uyari = len(uyarilar)
        try:
            turlar.append(
                olc_tek_tur(a.soru, dinle, ajan.chat, seslendir,
                            ses_bekleniyor=ses_aktif)
            )
        except KeyboardInterrupt:
            print("\nKullanici durdurdu.")
            break
        except Exception as exc:  # noqa: BLE001
            basarisiz += 1
            print(f"tur GECERSIZ: {type(exc).__name__}: {exc}")
        finally:
            # Sebep gorunmeden "gecersiz" demek yetmez: VoiceIO'nun kendi
            # hata metni (ornegin kopan baglanti) burada basilir.
            for u in uyarilar[onceki_uyari:]:
                print(f"  {u}")

    if not turlar:
        print(f"Hicbir tur olculemedi ({basarisiz} gecersiz tur).")
        return 1
    if basarisiz:
        print(f"\nUYARI: {basarisiz} tur gecersizdi ve ortalamaya girmedi.")

    ozet = ozetle(turlar)
    _yazdir(ozet)

    # Etiket iddiadan degil KANITTAN gelir: "tam" yalniz gercekten
    # seslendirilmis turlar icin yazilir (A-01).
    sonuc = {
        "schema_version": 1,
        "olculdu": datetime.now().isoformat(timespec="seconds"),
        "mod": "tam" if all(t.get("ses_kaniti") for t in turlar) else "kuru",
        "model": ajan._registry.local_main(),
        "gecersiz_tur": basarisiz,
        "uyarilar": uyarilar,
        "turlar": turlar,
        "ozet": ozet,
    }
    yol = rapor_yaz(sonuc, Path(a.out))
    print(f"  Rapor: {yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
