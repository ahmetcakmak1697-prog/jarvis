"""scripts/olc_tts_anatomisi.py — 3.468 ms'nin icini acar.

    python scripts/olc_tts_anatomisi.py --tur 5
    python scripts/olc_tts_anatomisi.py --tur 5 --yalniz-sentez

`automation/SES_HATTI_COZUMLEME_2026-09-09.md` bes noktali bir regresyondan
su modeli cikardi:

    sentez_ve_oynatma_ms = 3.468 + 72,2 x karakter          R2 = 0,986

Aritmetik dogru (bu betigin `dogrusal_uyum`'u ayni bes noktadan ayni sayilari
uretiyor, testle kilitli). Sinanan sey aritmetik degil **model**: 72,2
ms/karakter egiminin saf konusma hizi oldugu varsayimi. Eger sentez suresi de
metin uzunluguyla buyuyorsa egim iki seyi birbirine karistirmis olur ve
kesisim 3.468 ms oldugundan farkli cikar.

Kesisim dogrudan gozlenmedi; bir **cikarimdir**. Bu betik onu olcume cevirir.

Olculen dilimler (`EdgeTTSAdapter.speak()` icindeki bes damga)
--------------------------------------------------------------
    t0 -> t_istek           kapi kontrolleri (mikrosaniye mertebesi)
    t_istek -> t_ses_hazir  sentez_ms            -- BULUTA GIDIS-DONUS
    t_ses_hazir -> t_oynatma_basladi  oynatici_kurulum_ms  -- mixer + load
    t_oynatma_basladi -> t_bitti      oynatma_ms           -- sesin suresi
    --------------------------------------------------------------------
    t0 -> t_bitti           toplam_ms

Ilk sese kadar odenen bedel = `sentez_ms + oynatici_kurulum_ms`. Kartin
sordugu "3.468 ms'nin kaci ag, kaci yerel" sorusu tam olarak bu ikisinin
oranidir.

EGRESS: bu betik metni Microsoft'a gonderir. Gonderilen metin **sentetiktir**
(`CUMLELER`) -- Ahmet'in gercek cevaplari degil. Bayrak yalniz bu surecte,
`os.environ` uzerinden tanimlanir; hicbir dosyaya yazilmaz, `.env` okunmaz.

**Bu betik olcer, DUZELTMEZ.** Akisli TTS bir mimari degisikliktir ve
CLAUDE.md 9 geregi Ahmet'in imzasini ister.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO = Path(__file__).resolve().parents[1]
for _yol in (str(_REPO), str(_REPO / "scripts")):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

__all__ = ["CUMLELER", "dogrusal_uyum", "olc_dizi", "ozetle", "rapor_yaz"]

#: Uzunlugu bilinen sentetik Turkce cumleler: ~20, ~60, ~120, ~240 karakter.
#: Icerik kasitli olarak kisisel veri TASIMAZ -- disari cikan sey olcumdur.
#: Uzunluklar `test_sentetik_cumleler_dort_uzunluk_basamagi_verir` ile kilitli:
#: dosya kodlamasi bozulursa (BOM, cp1254) karakter sayisi kayar ve
#: ms/karakter olcumu sessizce yanlis olur.
CUMLELER: Tuple[str, ...] = (
    "Bugün hava çok güzel.",
    "Sabah erkenden kalkıp bahçedeki çiçekleri suladım bugün.",
    "Deniz kıyısındaki küçük kasabada yaşayan balıkçılar, her sabah güneş "
    "doğmadan önce ağlarını toplayıp açığa açılırlardı.",
    "Kütüphanenin en üst katındaki okuma salonunda, rafların arasından "
    "süzülen ışık eski kitapların sayfalarına düşerken, öğrenciler sınav "
    "haftası boyunca sabahlara kadar çalışır, aralarda pencereden şehrin "
    "ışıklarını seyrederek biraz dinlenirlerdi.",
)


def dogrusal_uyum(
    x: Sequence[float], y: Sequence[float]
) -> Optional[Tuple[float, float, float]]:
    """En kucuk kareler: `(egim, kesisim, R2)`. Uyum yoksa `None`.

    Iki noktadan az veriyle egim yoktur ve butun x'ler ayniysa tanimsizdir.
    Ikisinde de sonsuzluk ya da sifir uydurulmaz, `None` doner -- olculemeyen
    seyin adi `None`'dir.
    """
    n = len(x)
    if n < 2 or n != len(y):
        return None

    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None

    egim = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    kesisim = my - egim * mx

    ss_tot = sum((b - my) ** 2 for b in y)
    ss_res = sum((b - (egim * a + kesisim)) ** 2 for a, b in zip(x, y))
    r2 = 1.0 if ss_tot == 0 else 1 - ss_res / ss_tot
    return round(egim, 4), round(kesisim, 1), round(r2, 4)


def olc_dizi(konus, cumle: str, tur: int) -> List[Dict[str, Any]]:
    """Bir cumleyi `tur` kez seslendirip her turun dilimlerini toplar.

    Basarisiz tur ortalamaya GIRMEZ; `ok=False` sonuclari sebebiyle birlikte
    disari verilir ki sessizce kaybolmasin.
    """
    kayitlar: List[Dict[str, Any]] = []
    for _ in range(tur):
        r = konus(cumle)
        kayitlar.append({
            "ok": bool(r.ok),
            "karakter": len(cumle),
            "sentez_ms": _yuvarla(r.sentez_ms),
            "oynatici_kurulum_ms": _yuvarla(r.oynatici_kurulum_ms),
            "oynatma_ms": _yuvarla(r.oynatma_ms),
            "toplam_ms": _yuvarla(r.toplam_ms),
            "warning": r.warning if not r.ok else None,
        })
    return kayitlar


def _yuvarla(deger: Optional[float]) -> Optional[float]:
    return None if deger is None else round(deger, 1)


def _yuzdelik(dizi: List[float], p: float) -> float:
    d = sorted(dizi)
    if len(d) == 1:
        return round(d[0], 1)
    k = (len(d) - 1) * p
    alt, ust = int(k), min(int(k) + 1, len(d) - 1)
    return round(d[alt] + (d[ust] - d[alt]) * (k - alt), 1)


OZETLENEN = ("sentez_ms", "oynatici_kurulum_ms", "oynatma_ms", "toplam_ms")


def ozetle(kayitlar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Alan alan dagilim. `None` tasiyan tur o alanin ortalamasina girmez."""
    gecerli = [k for k in kayitlar if k.get("ok")]
    ozet: Dict[str, Any] = {"tur": len(kayitlar), "gecerli_tur": len(gecerli)}
    for alan in OZETLENEN:
        d = [k[alan] for k in gecerli if k.get(alan) is not None]
        if not d:
            continue
        ozet[alan] = {
            "p50": _yuzdelik(d, 0.50),
            "min": round(min(d), 1),
            "max": round(max(d), 1),
            "ort": round(statistics.mean(d), 1),
            "olculen_tur": len(d),
        }
    return ozet


def _uyumlar(kayitlar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Her dilim icin karakter -> ms dogrusal uyumu. Tum turlar nokta sayilir."""
    gecerli = [k for k in kayitlar if k.get("ok")]
    cikti: Dict[str, Any] = {}
    for alan in OZETLENEN:
        noktalar = [(k["karakter"], k[alan]) for k in gecerli
                    if k.get(alan) is not None]
        uyum = dogrusal_uyum([a for a, _ in noktalar], [b for _, b in noktalar])
        cikti[alan] = None if uyum is None else {
            "n": len(noktalar),
            "egim_ms_karakter": uyum[0],
            "kesisim_ms": uyum[1],
            "r2": uyum[2],
        }
    return cikti


def rapor_yaz(sonuc: Dict[str, Any], hedef_dizin: Path) -> Path:
    damga = datetime.now().strftime("%Y%m%d-%H%M")
    yol = hedef_dizin / f"TTS_ANATOMISI_{damga}.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return yol


def _konusucu(oynat: bool, bayt_kaydi: List[int], silinecek: List[str]):
    """`EdgeTTSAdapter.speak` sarmalayicisi.

    Sentez ucu, gercek `_default_edge_synth`'i cagirir ama uretilen gecici
    mp3'un YOLUNU ve BOYUTUNU disari verir. Boyut olcume girer cunku kartin
    sorusu "bedel ag mi" -- indirilen bayt sayisi o sorunun dogrudan kanitidir.
    Dosyalar tur bitince, OLCUM DISINDA silinir; adapter kendi gecici
    dosyalarini temizlemiyor (bkz. rapor, dokunulmayanlar).
    """
    from j0_tts_adapters import EdgeTTSAdapter, _default_edge_synth

    def _synth(metin: str, ses: str) -> str:
        yol = _default_edge_synth(metin, ses)
        silinecek.append(yol)
        try:
            bayt_kaydi.append(os.path.getsize(yol))
        except OSError:
            bayt_kaydi.append(-1)
        return yol

    adapter = EdgeTTSAdapter(synth=_synth, play=oynat)
    return adapter.speak


def _temizle(yollar: List[str]) -> None:
    for yol in yollar:
        try:
            os.remove(yol)
        except OSError:
            pass
    yollar.clear()


def _kosu(oynat: bool, tur: int) -> Dict[str, Any]:
    etiket = "oynatmali" if oynat else "oynatmasiz"
    print(f"\n### {etiket} — {len(CUMLELER)} uzunluk x {tur} tur")
    hepsi: List[Dict[str, Any]] = []
    basamaklar: Dict[str, Any] = {}
    for cumle in CUMLELER:
        bayt: List[int] = []
        silinecek: List[str] = []
        konus = _konusucu(oynat, bayt, silinecek)
        kayitlar = olc_dizi(konus, cumle, tur)
        _temizle(silinecek)
        for k, b in zip(kayitlar, bayt):
            k["ses_bayt"] = b
        hepsi.extend(kayitlar)
        ozet = ozetle(kayitlar)
        basamaklar[str(len(cumle))] = {
            "cumle": cumle, "karakter": len(cumle),
            "ses_bayt_p50": _yuzdelik([float(b) for b in bayt if b > 0], 0.50)
            if any(b > 0 for b in bayt) else None,
            "turlar": kayitlar, "ozet": ozet,
        }
        s = ozet.get("sentez_ms", {})
        o = ozet.get("oynatma_ms", {})
        print(f"  {len(cumle):>4} karakter  sentez p50 {s.get('p50', '?'):>8} ms"
              f"   oynatma p50 {o.get('p50', 'YOK'):>8} ms"
              f"   gecerli {ozet['gecerli_tur']}/{ozet['tur']}")
    return {"basamaklar": basamaklar, "uyumlar": _uyumlar(hepsi),
            "tum_turlar": len(hepsi)}


def _yazdir_uyum(baslik: str, uyum: Optional[Dict[str, Any]]) -> None:
    if not uyum:
        print(f"  {baslik:<34} OLCULMEDI")
        return
    print(f"  {baslik:<34} {uyum['egim_ms_karakter']:>8.2f} ms/kar"
          f"   kesisim {uyum['kesisim_ms']:>9.1f} ms"
          f"   R2 {uyum['r2']:.3f}   n={uyum['n']}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Edge TTS turunun asama asama anatomisi")
    ap.add_argument("--tur", type=int, default=5, help="uzunluk basina tur")
    ap.add_argument("--yalniz-sentez", action="store_true",
                    help="yalniz oynatmasiz kosu (ses cihazi gerekmez)")
    ap.add_argument("--out", default=str(_REPO / "automation"))
    a = ap.parse_args()

    from j0_tts_adapters import EDGE_TTS_ENABLE_FLAG

    # Bayrak YALNIZ bu surecte tanimlanir. Hicbir dosyaya yazilmaz, `.env`
    # okunmaz/yazilmaz (CLAUDE.md 9). Cocuk surec yok, yani sizmaz.
    os.environ[EDGE_TTS_ENABLE_FLAG] = "1"
    print("Edge TTS bayragi YALNIZ bu surecte acildi; dosyaya yazilmadi.")
    print("Disari cikan metin sentetiktir (CUMLELER), kisisel veri degil.")

    sonuc: Dict[str, Any] = {
        "schema_version": 1,
        "olculdu": datetime.now().isoformat(timespec="seconds"),
        "olculmeyen": (
            "t_oynatma_basladi oynaticinin BILDIRDIGI andir (pygame play() "
            "donusu), dogrulanmis akustik baslangic degil. Mixer ile "
            "hoparlor arasi bu katmanin altindadir ve olculmuyor."
        ),
    }

    if not a.yalniz_sentez:
        sonuc["oynatmali"] = _kosu(True, a.tur)
    sonuc["oynatmasiz"] = _kosu(False, a.tur)

    print("\n" + "=" * 74)
    print("  DOGRUSAL UYUM — karakter basina ms")
    print("=" * 74)
    for etiket in ("oynatmali", "oynatmasiz"):
        blok = sonuc.get(etiket)
        if not blok:
            continue
        print(f"  [{etiket}]")
        for alan in OZETLENEN:
            _yazdir_uyum(f"    {alan}", blok["uyumlar"].get(alan))
    print("-" * 74)
    print("  Ahmet'in regresyonu (5 nokta, sentez+oynatma):")
    print("     72.22 ms/kar   kesisim    3467.7 ms   R2 0.986")
    print("=" * 74)

    yol = rapor_yaz(sonuc, Path(a.out))
    print(f"\n  Rapor: {yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
