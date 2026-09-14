"""scripts/j0_mic_check.py — mikrofon seviye teşhisi.

"Sesimi almıyor" şikayeti üç ayrı sebepten gelebilir ve üçünün çözümü farklı:

  1. Yanlış aygıt seçilmiş   -> aygıt hiç veri vermez (rms sürekli 0.00000)
  2. Aygıt doğru, kazanç düşük -> veri gelir ama eşiğin (0.01) altında kalır
  3. Aygıt susturulmuş/izin yok -> yine sürekli 0

Bu betik hangisi olduğunu ÖLÇER. Konuşurken canlı seviye çubuğu gösterir,
sonunda ölçülen tepe değere göre uygun eşiği önerir.

Kullanım:
    $env:JARVIS_MIC_DEVICE="9"; .\.venv\Scripts\python.exe scripts\j0_mic_check.py
    .\.venv\Scripts\python.exe scripts\j0_mic_check.py --device 2 --seconds 8
    .\.venv\Scripts\python.exe scripts\j0_mic_check.py --scan
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice.stt import (  # noqa: E402
    DEFAULT_SILENCE_THRESHOLD,
    resolve_mic_device,
    rms,
)

SAMPLE_RATE = 16000
CHUNK = 480  # 30 ms


def _cubuk(deger: float, esik: float, genislik: int = 34) -> str:
    """Seviye çubuğu. Eşik konumu '|' ile işaretlenir."""
    dolu = min(genislik, int((deger / max(esik * 3, 1e-9)) * genislik))
    esik_konum = min(genislik - 1, int((esik / max(esik * 3, 1e-9)) * genislik))
    hucreler = ["#" if i < dolu else "." for i in range(genislik)]
    if hucreler[esik_konum] == ".":
        hucreler[esik_konum] = "|"
    return "".join(hucreler)


def dinle(device, saniye: float, esik: float) -> dict:
    import numpy as np
    import sounddevice as sd

    tepe = 0.0
    toplam = 0.0
    sayac = 0
    esik_ustu = 0
    seviyeler = []
    parca_sayisi = int(saniye * 1000 / 30)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=CHUNK, device=device) as akis:
        sonraki_rapor = 0
        for i in range(parca_sayisi):
            veri, _tasma = akis.read(CHUNK)
            parca = np.asarray(veri, dtype="float32").reshape(-1).tolist()
            r = rms(parca)
            seviyeler.append(r)
            tepe = max(tepe, r)
            toplam += r
            sayac += 1
            if r >= esik:
                esik_ustu += 1
            if i >= sonraki_rapor:  # ~her 300 ms
                gecen = (i * 30) / 1000
                print(f"  {gecen:4.1f}s  {_cubuk(r, esik)}  rms={r:.5f}"
                      f"{'  <-- ESIK USTU' if r >= esik else ''}")
                sonraki_rapor = i + 10

    return {
        "tepe": tepe,
        "ortalama": toplam / sayac if sayac else 0.0,
        "medyan": statistics.median(seviyeler) if seviyeler else 0.0,
        "esik_ustu_parca": esik_ustu,
        "toplam_parca": sayac,
    }


def medyan_teshisi(medyan: float, tepe: float, esik: float):
    """Tepe esigi geciyor ama MEDYAN altindaysa onerilen esik; degilse None.

    Neden medyan, ortalama degil (olculdu 2026-09-14, 15 cumle,
    automation/STT_TURKCE_OLCUM_2026-09-14.md): ortalama yuksek tepeler
    yuzunden esigin USTUNDE kalirken parcalarin cogu altinda olabilir --
    15 cumlenin 15'inde ortalama 0,0137-0,0352 idi, yani bir ortalama
    kontrolu hic ateslemezdi. Medyan esigin altindaysa konusma suresinin
    yarisindan fazlasi kaydediciye SESSIZLIK gibi gorunur; cumle ici yumusak
    heceler ve duraklamalar cumleyi erken bitirebilir.

    Oneri `medyan * 0.5`: mevcut `tepe * 0.4` dali gibi olculen seviyeye
    oranli, mutlak degil; parcalarin en az yarisini esigin ustune alir.
    0.5 carpani bir basarisiz kayitla DOGRULANMADI -- 2026-09-14 kaydinda
    hicbir esikte kesilme cikmadi. Taban, `tepe * 0.4` daliyla ayni: 0.0005.
    Tepe esigin altindaysa bu dal ateslenmez; o durum mevcut dalin isidir.
    """
    if tepe < esik or medyan >= esik:
        return None
    return max(round(medyan * 0.5, 5), 0.0005)


def tara() -> None:
    import sounddevice as sd

    print("=== 16 kHz mono kabul eden giris aygitlari ===")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] < 1:
            continue
        try:
            sd.check_input_settings(device=i, channels=1,
                                    samplerate=SAMPLE_RATE, dtype="float32")
        except Exception:
            continue
        api = sd.query_hostapis(d["hostapi"])["name"]
        print(f"  [{i:2}] {api:<22} {d['name'][:44]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=None,
                    help="aygit indeksi (yoksa JARVIS_MIC_DEVICE)")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--threshold", type=float, default=DEFAULT_SILENCE_THRESHOLD)
    ap.add_argument("--scan", action="store_true", help="yalniz aygitlari listele")
    a = ap.parse_args()

    if a.scan:
        tara()
        return 0

    device = a.device if a.device is not None else resolve_mic_device()
    print(f"Aygit: {device!r}  (JARVIS_MIC_DEVICE -> {resolve_mic_device()!r})")

    import sounddevice as sd
    if device is not None:
        bilgi = sd.query_devices()[device]
        print(f"  {bilgi['name']}  "
              f"[{sd.query_hostapis(bilgi['hostapi'])['name']}]")
    else:
        print("  (isletim sistemi varsayilani)")

    print(f"Esik: {a.threshold}")
    print(f"\n{a.seconds:.0f} saniye boyunca NORMAL SESLE konusun.")
    for geri in (3, 2, 1):
        print(f"  {geri}...", end="\r", flush=True)
        time.sleep(1)
    print("  KONUSUN!            \n")

    try:
        s = dinle(device, a.seconds, a.threshold)
    except Exception as exc:
        print(f"\nAYGIT ACILAMADI: {exc}")
        print("`--scan` ile calisan aygitlari listeleyin.")
        return 1

    oran = s["esik_ustu_parca"] / max(s["toplam_parca"], 1) * 100
    print("\n=== SONUC ===")
    print(f"  tepe rms      : {s['tepe']:.5f}")
    print(f"  ortalama rms  : {s['ortalama']:.5f}")
    print(f"  medyan rms    : {s['medyan']:.5f}")
    print(f"  esik ustu     : {s['esik_ustu_parca']}/{s['toplam_parca']} "
          f"parca (%{oran:.0f})")

    print("\n=== TESHIS ===")
    if s["tepe"] < 0.0005:
        print("  Aygit HIC veri vermiyor: yanlis aygit, susturulmus ya da")
        print("  Windows mikrofon izni kapali.")
        print("  -> `--scan` ile baska aygit deneyin; Windows Ayarlar >")
        print("     Gizlilik > Mikrofon iznini kontrol edin.")
        return 1
    if s["tepe"] < a.threshold:
        onerilen = max(round(s["tepe"] * 0.4, 5), 0.0005)
        print(f"  Aygit CALISIYOR ama seviye esigin altinda "
              f"(tepe {s['tepe']:.5f} < esik {a.threshold}).")
        print(f"  -> Onerilen esik: {onerilen}")
        print("  -> Ya da Windows'ta mikrofon kazancini yukseltin.")
        return 2
    if oran < 5:
        print("  Konusma algilandi ama cok seyrek. Mikrofona daha yakin")
        print("  konusun ya da esigi biraz dusurun.")
        return 2
    onerilen_medyan = medyan_teshisi(s["medyan"], s["tepe"], a.threshold)
    if onerilen_medyan is not None:
        print(f"  Tepe esigi geciyor ama MEDYAN esigin altinda "
              f"(medyan {s['medyan']:.5f} < esik {a.threshold}).")
        print("  Konusma suresinin yarisindan fazlasi kaydediciye SESSIZLIK gibi")
        print("  gorunuyor; cumle ici yumusak heceler cumleyi erken bitirebilir.")
        print("  Iki olasilik: surekli konusmadiniz (tekrar deneyin) ya da")
        print("  konusma seviyeniz esige yakin.")
        print(f"  -> Surekliyse onerilen esik: {onerilen_medyan}  (medyan x 0.5)")
        return 2
    print("  Mikrofon ve esik UYUMLU. Bu aygitla JARVIS sizi duymali.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
