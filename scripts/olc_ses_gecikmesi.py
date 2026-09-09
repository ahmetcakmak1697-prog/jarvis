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
    t0  `dinle()` cagrilmadan once
    t1  girdi metni hazir       -> girdi_ms
    t2  model cevabi tamam      -> model_ms
    t3  `seslendir()` dondu     -> sentez_ve_oynatma_ms
    ------------------------------------------------
        tur_ms = t3 - t0

NE OLCULMUYOR (A-02) -- bu aralik PUSULA'nin araligi DEGILDIR
-------------------------------------------------------------
* PUSULA'da baslangic "konusma bitti" anidir (VAD karari). Buradaki t0
  `dinle()` oncesidir: mikrofon beklemesini, kullanicinin konusmasini,
  STT'yi ve gerekirse klavye beklemesini kapsar. `STTResult` VAD
  konusma-sonu anini disari vermiyor.
* PUSULA'da bitis "ilk ses duyuldu" anidir. Buradaki t3 `say()` donusudur
  ve varsayilan oynatici sesin BITMESINI bekler.
  `TTSResult.first_audio_hint_ms` bu boslugu kapatmaz; kendi uyarisinda
  "synthesis time only ... playback start is not measured" diyor.

Codex'in deterministik senaryosunda gercek aralik 700 ms, bu betigin
olctugu 7200 ms idi -- on kat. Sayilar uydurulmadi, ETIKETLER gercege
indirildi (B11 dersi: yanlis etiketli bir olcum, dogru bir olcum gibi
karar verdirir).

`tur_ms` gercek araligi KAPSAR, yani onun UST SINIRIDIR: altinda kalmak
PUSULA'nin saglandigini kanitlar, ustune cikmak hicbir sey kanitlamaz --
hukum bu yuzden "HEDEFTE" ya da "BELIRSIZ", asla "HEDEF DISI" degil.

Gercek sinirlari olcmek `voice/stt.py` ve `scripts/j0_tts_adapters.py`
icine olay damgasi koymayi gerektirir; ikisi de bu kartin kapsami disinda.

Rapor p50 ve p95 verir; tek kosu hukum degildir (A11 dersi: ayni model ayni
puanlayicida bile kosular arasi oynuyor).
"""
from __future__ import annotations

import argparse
import json
import os
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

#: Olculemeyen sey uydurulmaz, ADIYLA raporlanir (A-02). Bu metin ozete ve
#: JSON raporuna girer ki sayiyi okuyan neyi okumadigini da gorsun.
OLCULMEYEN_SINIRLAR = (
    "VAD konusma-sonu ani ve ilk ses olayi OLCULMUYOR: STTResult VAD "
    "sonunu vermiyor, TTSResult.first_audio_hint_ms yalniz sentez suresi "
    "(kendi uyarisi: 'playback start is not measured'). Olculen tur_ms "
    "PUSULA araligini kapsar, yani onun UST SINIRIDIR."
)


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

    def __init__(self, vio: Any, uyarilar: List[str],
                 son_sonuc: Optional[Callable[[], Any]] = None) -> None:
        self._vio = vio
        self._uyarilar = uyarilar
        #: `VoiceIO.say()` hicbir sey dondurmez ve o sozlesme DEGISMEZ. TTS'in
        #: kendi damgalarina ulasmak icin konusmaci disaridan sarilir ve son
        #: `TTSResult` buradan okunur. Verilmezse davranis eskisi gibi kalir.
        self._son_sonuc = son_sonuc

    def __call__(self, metin: Optional[str]) -> Any:
        from voice.voice_loop import speech_text

        if not getattr(self._vio, "enabled", False):
            self._uyarilar.append("[olcum] ses katmani kapali; seslendirme yok")
            return False

        if not speech_text(metin):
            self._uyarilar.append("[olcum] seslendirilecek metin yok")
            return False

        onceki = len(self._uyarilar)
        self._vio.say(metin)
        if len(self._uyarilar) != onceki:
            return False

        # Bildirim gelmedi: `speak()` kendi sozlesmesine gore basarili dondu.
        # Damga varsa ONU dondur -- ici bos bir `True`, olculmus dilimleri
        # cope atardi.
        sonuc = self._son_sonuc() if self._son_sonuc is not None else None
        return True if sonuc is None else sonuc


def _ses_kaniti(sonuc: Any) -> bool:
    """Seslendirme gercekten oldu mu?

    Iki sozlesme birlikte desteklenir: eski `seslendir` bool/None dondururdu,
    yenisi `TTSResult` donduruyor. Nesnenin kendisi her zaman truthy oldugu
    icin `bool(sonuc)` YETMEZ -- `ok=False` bir TTSResult boyle "kanit"
    sayilirdi. A-01 tam olarak bu hatanin karti.
    """
    if sonuc is None:
        return False
    ok = getattr(sonuc, "ok", None)
    return bool(sonuc) if ok is None else bool(ok)


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

    ses_sonucu = seslendir(cevap)
    t3 = time.perf_counter()

    ses_kaniti = _ses_kaniti(ses_sonucu)
    if ses_bekleniyor and not ses_kaniti:
        raise OlcumBasarisiz(
            "seslendirme kaniti yok -- bu tur gecerli olcum degil"
        )

    # Alan adlari OLCULEN seyi soyler, hedeflenen seyi degil (A-02).
    ms = lambda a, b: round((b - a) * 1000, 1)  # noqa: E731
    return {
        "soru": metin,
        # Cevabin KENDISI kaydedilir, yalniz uzunlugu degil: olctugu girdiyi
        # saklamayan bir olcum araci kendi sonucunu bir daha uretemez. 2026-09-09'da
        # tam bu eksik yuzunden "gercek cevaplar sentezi yavaslatiyor mu"
        # sorusu sinanamadi. Uzunluk alani KALIR -- eski kayitlarla kiyas
        # onun uzerinden yapiliyor.
        "cevap": cevap or "",
        "cevap_uzunluk": len(cevap or ""),
        "ses_kaniti": ses_kaniti,
        "girdi_ms": ms(t0, t1),
        "model_ms": ms(t1, t2),
        "sentez_ve_oynatma_ms": ms(t2, t3),
        "tur_ms": ms(t0, t3),
        # TTS'in KENDI damgalari (`EdgeTTSAdapter.speak`). Damga veremeyen bir
        # seslendirici icin `None` -- `0` degil. `sentez_ve_oynatma_ms` tek
        # sayi olarak kaldigi surece ag payi ile calinan sesin suresi
        # birbirinden ayrilamiyordu.
        "sentez_ms": getattr(ses_sonucu, "sentez_ms", None),
        "oynatici_kurulum_ms": getattr(ses_sonucu, "oynatici_kurulum_ms", None),
        "oynatma_ms": getattr(ses_sonucu, "oynatma_ms", None),
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
    for alan in ("girdi_ms", "model_ms", "sentez_ve_oynatma_ms", "tur_ms",
                 "sentez_ms", "oynatici_kurulum_ms", "oynatma_ms"):
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

    # Hukum UST SINIR uzerinden verilir (A-02): olculen aralik PUSULA
    # araligini kapsar. Altinda kalmak saglandigini KANITLAR; ustune cikmak
    # hicbir sey kanitlamaz, o yuzden "HEDEF DISI" degil "BELIRSIZ".
    tur = ozet.get("tur_ms", {})
    ozet["hedef_ms"] = HEDEF_MS
    ozet["pusula_araligi_olculdu"] = False
    ozet["olculmeyen_sinirlar"] = OLCULMEYEN_SINIRLAR
    for etiket in ("p50", "p95"):
        deger = tur.get(etiket)
        ozet[f"{etiket}_hukum"] = (
            None if deger is None
            else ("HEDEFTE" if deger <= HEDEF_MS else "BELIRSIZ")
        )
    return ozet


def rapor_yaz(sonuc: Dict[str, Any], hedef_dizin: Path) -> Path:
    damga = datetime.now().strftime("%Y%m%d-%H%M")
    yol = hedef_dizin / f"SES_GECIKMESI_{damga}.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return yol


def _kuru_ses_cikisi(uyarilar: List[str]):
    """STT'siz ama GERCEK TTS'li seslendirici kurar.

    Dinleyici hic kurulmaz: ne mikrofon ne de Whisper yuklenir, yani Ahmet'i
    beklemez. Cikis tarafi ise tam gercek yoldur -- `VoiceIO.say()` cagrilir,
    yani `speech_text()` temizligi ve B05 veri-sinifi kapisi de olculen surenin
    icindedir. Bunlar "atlandi" denip disarida birakilsaydi olculen sey canli
    hattin kendisi olmazdi.

    Konusmaci sarilir cunku `VoiceIO.say()` hicbir sey dondurmez ve o sozlesme
    degismez; `TTSResult` ancak boyle disari cikar. `is_local` TANIMLANMAZ --
    varsayilan `False` kalir ve egress kapisi yerinde durur.
    """
    from j0_tts_adapters import EDGE_TTS_ENABLE_FLAG, EdgeTTSAdapter
    from voice.voice_loop import VoiceIO

    # Bayrak YALNIZ bu surecte. Hicbir dosyaya yazilmaz, `.env` okunmaz (9).
    os.environ[EDGE_TTS_ENABLE_FLAG] = "1"
    print("Edge TTS bayragi YALNIZ bu surecte acildi; dosyaya yazilmadi.")

    adapter = EdgeTTSAdapter()
    gercek_speak = adapter.speak
    kayit: Dict[str, Any] = {}

    def _kaydeden_speak(metin: str):
        sonuc = gercek_speak(metin)
        kayit["son"] = sonuc
        return sonuc

    adapter.speak = _kaydeden_speak
    vio = VoiceIO(speaker=adapter, enabled=True, notify=uyarilar.append)
    return SesOlcumu(vio, uyarilar, son_sonuc=lambda: kayit.get("son")), True


def _yazdir(ozet: Dict[str, Any]) -> None:
    print()
    print("=" * 58)
    print(f"  SES HATTI GECIKMESI — {ozet['tur']} tur")
    print("=" * 58)
    basliklar = {"girdi_ms": "Girdi (dinle cagrisi)",
                 "model_ms": "Model (metin -> cevap)",
                 "sentez_ve_oynatma_ms": "Sentez + TAM oynatma",
                 # TTS'in kendi damgalari: ust satirin ICINDE durur, yanina
                 # degil. Ag payi ile calinan sesin suresi artik ayri gorunur.
                 "sentez_ms": "   . sentez (AG)",
                 "oynatici_kurulum_ms": "   . oynatici kurulumu",
                 "oynatma_ms": "   . oynatma (calinan ses)",
                 "tur_ms": "TUR SURESI (ust sinir)"}
    for alan, baslik in basliklar.items():
        d = ozet.get(alan)
        if not d:
            continue
        ayrac = "-" * 58 if alan == "tur_ms" else ""
        if ayrac:
            print(ayrac)
        print(f"  {baslik:<26} p50 {d['p50']:>8.1f} ms   p95 {d['p95']:>8.1f} ms")
    print("-" * 58)
    hedef = ozet.get("hedef_ms")
    for etiket in ("p50", "p95"):
        hukum = ozet.get(f"{etiket}_hukum")
        if hukum is None:
            continue
        print(f"  {etiket} ust sinir <= {hedef} ms ? {hukum}")
    print("=" * 58)
    print("  BELIRSIZ = ust sinir asildi; PUSULA araligi bundan KUCUKTUR")
    print("  ama ne kadar oldugu olculmuyor:")
    print(f"  {ozet.get('olculmeyen_sinirlar', '')}")
    print("  Hangi istatistigin kabul siniri oldugu Ahmet'in urun")
    print("  kararidir. Bu betik olcer, hukum vermez.")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Ses hatti uctan uca gecikme olcumu")
    ap.add_argument("--tur", type=int, default=5, help="kac tur olculecek")
    ap.add_argument("--soru", default="nerede kaldik",
                    help="kuru modda sorulacak metin")
    ap.add_argument("--kuru", action="store_true",
                    help="mikrofonsuz: STT atlanir")
    ap.add_argument("--ses-cikisi", action="store_true",
                    help="kuru modda TTS'i GERCEKTEN kostur (STT yok, ses var)")
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

    if a.kuru and a.ses_cikisi:
        # STT yok, TTS VAR. `--kuru` tek basina TTS'i hic calistirmiyor
        # (seslendir sabit False donen bir no-op) -- yani "kuru mod model+TTS
        # olcer" varsayimiyla alinan her sayi, sentezi hic gormeden
        # "olctum" derdi. Bu kapi o bosluğu kapatir.
        try:
            seslendir, ses_aktif = _kuru_ses_cikisi(uyarilar)
        except Exception as exc:  # noqa: BLE001
            print(f"Ses cikisi kurulamadi ({exc}); sessiz kuru moda dusuluyor.")
    elif not a.kuru:
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
