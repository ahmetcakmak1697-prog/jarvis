"""scripts/olc_stt_turkce.py — STT Türkçe sondası (KART_STT_TURKCE).

İki kusur, iki ölçüm — KARIŞTIRILMAZ:

  Kusur A (kelime bozulması): aynı kayıtlar üzerinde model x beam_size
          matrisi, CPU/int8. Her satırda WER VE süre birden (PUSULA bütçesi
          1500 ms; STT o bütçenin içinde).
  Kusur B (cümle algılanmıyor / erken kesiliyor): üretim kaydedicisi
          (voice/stt.py MicrophoneRecorder) kayıt üzerinde YENİDEN OYNATILIR —
          mantığı kopyalanmaz. Mevcut eşik cümleyi nerede keserdi, hangi eşikte
          kesmezdi.

Kayıt sessizlik algılayıcısından BAĞIMSIZ alınır (Enter ile başla, Enter ile
bitir): algılayıcı cümleyi keserse Kusur B'nin hasarı Kusur A'nın WER'ine
karışırdı.

Kullanım (kayıt adımı Ahmet'in sesidir):
    .\\.venv\\Scripts\\python.exe scripts\\olc_stt_turkce.py kaydet
    .\\.venv\\Scripts\\python.exe scripts\\olc_stt_turkce.py olc
    .\\.venv\\Scripts\\python.exe scripts\\olc_stt_turkce.py ipucu   # KART_STT_HOTWORDS

**Ses kayıtları repoya YAZILMAZ.** Varsayılan yer işletim sisteminin geçici
dizinidir; çıktı yolu repo içindeyse betik mikrofonu açmadan reddeder. Rapora
yalnız metin karşılaştırması girer.

**Hiçbir varsayılan değişmez.** voice/stt.py import edilir, değiştirilmez.
`beam_size` orada kodda sabit (1) olduğu için matris transkripsiyon çağrısını
burada kurar — üretimdeki çağrının AYNISI, yalnız model ve beam_size değişken.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import tempfile
import time
import wave
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from voice.stt import (  # noqa: E402
    DEFAULT_CHUNK_MS,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SILENCE_DURATION_S,
    DEFAULT_SILENCE_THRESHOLD,
    MicrophoneRecorder,
    resolve_mic_device,
    rms,
    select_input_device,
)

ORNEKLEME = DEFAULT_SAMPLE_RATE
PARCA = DEFAULT_SAMPLE_RATE * DEFAULT_CHUNK_MS // 1000   # 480 örnek = 30 ms

#: Varsayılan kayıt kökü — repo DIŞINDA.
KAYIT_KOKU = Path(tempfile.gettempdir()) / "jarvis_stt_kayit"

#: Kusur B taraması: üretim kaydedicisi bu eşiklerle kayıt üzerinde koşar.
ESIKLER = (0.002, 0.003, 0.005, 0.007, 0.01)

#: Ahmet'in okuyacağı cümleler. Gerçek kullanımı temsil eder: selamlama, proje
#: sorusu, ev kontrolü, teknik terim, Türkçe özel harfler (ş, ğ, ı, İ, ç, ö, ü).
#: RAKAM YOK: "22" ile "yirmi iki" yazım farkı WER'i tanımayla ilgisiz
#: biçimde bozardı.
CUMLELER = (
    "Merhaba dostum, iyi misin?",
    "Hey Jarvis, nerede kaldık?",
    "Bugün hangi işleri bitirdik?",
    "Işıkları kapat ve perdeyi indir.",
    "İstanbul'da yarın hava nasıl olacak?",
    "Son commit'te neyi değiştirdik?",
    "Ollama çalışıyor mu, kontrol eder misin?",
    "DeepSeek'in cevabı neden bu kadar uzun sürdü?",
    "Testler iki sırada da yeşil geçti mi?",
    "Çocuklar okuldan dönünce bana haber ver.",
    "Şu dosyayı açıp özetini çıkarır mısın?",
    "Ağustos ayındaki ölçümleri göster.",
    "Klimayı biraz daha serin yap.",
    "Yarın sabahki toplantıyı bana hatırlat.",
    "Güle güle, sonra görüşürüz.",
)


# --------------------------------------------------------------------------- #
# Ölçüm çekirdeği — saf, test edilir (tests/test_olc_stt_turkce.py)
# --------------------------------------------------------------------------- #

def normalize_tr(metin: str) -> list[str]:
    """WER için kelimelere böler.

    ASCII-fold YOK: "ş" ile "s" farklı kelimedir. Büyük/küçük harf ve noktalama
    tanıma hatası sayılmaz: Türkçe kural ("I" -> "ı", "İ" -> "i"; düz `.lower()`
    "İ"yi "i" + birleşik nokta yapar), kesme işareti SİLİNİR ("İstanbul'da" ile
    "İstanbulda" aynı kelime), öteki noktalama boşluk olur.
    """
    metin = metin.replace("I", "ı").replace("İ", "i").lower()
    metin = re.sub(r"['’‘`]", "", metin)
    metin = re.sub(r"[^\w\s]", " ", metin)
    return metin.split()


def wer(referans: str, hipotez: str) -> dict:
    """Kelime hata oranı: (yerine koyma + silme + ekleme) / referans kelime."""
    r, h = normalize_tr(referans), normalize_tr(hipotez)
    onceki = list(range(len(h) + 1))
    for i, r_kelime in enumerate(r, 1):
        simdiki = [i] + [0] * len(h)
        for j, h_kelime in enumerate(h, 1):
            simdiki[j] = min(onceki[j] + 1, simdiki[j - 1] + 1,
                             onceki[j - 1] + (r_kelime != h_kelime))
        onceki = simdiki
    hata = onceki[-1]
    return {"hata": hata, "kelime": len(r),
            "oran": hata / len(r) if r else float(hata > 0)}


def karsilastir(once: list, sonra: list) -> dict:
    """Aynı cümlelerin iki koşusunu cümle cümle karşılaştırır.

    Toplam WER takası gizler: üç cümle düzelip iki cümle bozulursa toplam yine
    düşer. Bu yüzden düzelen, bozulan ve metni değişip hata sayısı aynı kalan
    cümleler AYRI listelenir.
    """
    onceki = {s["no"]: s for s in once}
    sonuc: dict = {"duzelen": [], "bozulan": [], "metni_degisen_ayni_hata": []}
    for s in sonra:
        a = onceki[s["no"]]
        kayit = {"no": s["no"], "once": a["hipotez"], "sonra": s["hipotez"],
                 "once_hata": a["hata"], "sonra_hata": s["hata"]}
        if s["hata"] < a["hata"]:
            sonuc["duzelen"].append(kayit)
        elif s["hata"] > a["hata"]:
            sonuc["bozulan"].append(kayit)
        elif s["hipotez"].strip() != a["hipotez"].strip():
            sonuc["metni_degisen_ayni_hata"].append(kayit)
    return sonuc


def repo_disinda(yol) -> Path:
    """Ses kaydı repo içine yazılamaz; yol repo içindeyse ValueError."""
    tam, kok = Path(yol).resolve(), KOK.resolve()
    if tam == kok or kok in tam.parents:
        raise ValueError(f"ses kayitlari repo icine yazilmaz: {tam}")
    return tam


def _parcalar(ornekler) -> list:
    return [ornekler[i:i + PARCA] for i in range(0, len(ornekler), PARCA)]


def sessizlik_simulasyonu(ornekler, esik: float,
                          sure_s: float = DEFAULT_SILENCE_DURATION_S) -> dict:
    """Üretim kaydedicisini kayıt üzerinde yeniden oynatır (Kusur B).

    `MicrophoneRecorder`'ın kendisi, mikrofon yerine kayıttan beslenen
    parçalarla koşar. Kaydedici cümleyi bitirdikten SONRA hâlâ eşik üstü parça
    varsa konuşma sürerken kesmiş demektir: `erken_kesildi`.
    """
    parcalar = _parcalar(list(ornekler))
    kayit = MicrophoneRecorder(silence_threshold=esik, silence_duration_s=sure_s,
                               chunk_source=lambda: iter(parcalar)).record()
    toplam_s = len(ornekler) / ORNEKLEME
    if not kayit.ok:
        return {"basladi": False, "sebep": kayit.reason, "tutulan_s": 0.0,
                "toplam_s": toplam_s, "atilan_esik_ustu_parca": 0,
                "erken_kesildi": False}
    ilk = next(i for i, p in enumerate(parcalar) if rms(p) >= esik)
    son = ilk + math.ceil(len(kayit.samples) / PARCA)
    atilan = sum(1 for p in parcalar[son:] if rms(p) >= esik)
    return {"basladi": True, "sebep": kayit.reason,
            "tutulan_s": len(kayit.samples) / ORNEKLEME, "toplam_s": toplam_s,
            "atilan_esik_ustu_parca": atilan,
            # Yalnız sessizlikle biten kayıt "erken kesilmiş" sayılır; azami
            # süreye çarpan ayrı bir sebeptir ve `sebep` alanında görünür.
            "erken_kesildi": atilan > 0 and kayit.reason is None}


def _yuzdelik(degerler: list, q: float) -> float:
    s = sorted(degerler)
    return s[min(len(s) - 1, max(0, round(q * (len(s) - 1))))] if s else 0.0


def rms_istatistik(ornekler, esik: float = DEFAULT_SILENCE_THRESHOLD) -> dict:
    """Kaydın parça-rms dağılımı: ortalama/tepe (j0_mic_check ile aynı tanım),
    eşik üstü oranı, yüzdelikler ve baş/son 0,4 s'nin gürültü tabanı."""
    seviyeler = [rms(p) for p in _parcalar(list(ornekler))]
    if not seviyeler:
        return {"ortalama": 0.0, "tepe": 0.0, "esik_ustu_yuzde": 0.0}
    kenar = max(1, int(0.4 * 1000 / DEFAULT_CHUNK_MS))
    return {
        "ortalama": sum(seviyeler) / len(seviyeler),
        "tepe": max(seviyeler),
        "esik_ustu_yuzde": 100.0 * sum(s >= esik for s in seviyeler) / len(seviyeler),
        "p10": _yuzdelik(seviyeler, 0.10), "p25": _yuzdelik(seviyeler, 0.25),
        "p50": _yuzdelik(seviyeler, 0.50), "p75": _yuzdelik(seviyeler, 0.75),
        "p90": _yuzdelik(seviyeler, 0.90),
        "gurultu_bas_p50": _yuzdelik(seviyeler[:kenar], 0.5),
        "gurultu_bas_tepe": max(seviyeler[:kenar]),
        "gurultu_son_p50": _yuzdelik(seviyeler[-kenar:], 0.5),
        "gurultu_son_tepe": max(seviyeler[-kenar:]),
    }


# --------------------------------------------------------------------------- #
# WAV — stdlib, 16 kHz mono 16 bit
# --------------------------------------------------------------------------- #

def _wav_yaz(yol: Path, ornekler) -> None:
    import numpy as np

    pcm = (np.clip(ornekler, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ORNEKLEME)
        w.writeframes(pcm)


def _wav_oku(yol: Path):
    import numpy as np

    with wave.open(str(yol), "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (ORNEKLEME, 1, 2):
            raise ValueError(f"{yol.name}: 16 kHz mono 16 bit bekleniyordu")
        veri = w.readframes(w.getnframes())
    return np.frombuffer(veri, dtype="<i2").astype("float32") / 32768.0


# --------------------------------------------------------------------------- #
# kaydet — Ahmet'in sesi
# --------------------------------------------------------------------------- #

def kaydet(a) -> int:
    # Yol denetimi mikrofon açılmadan ÖNCE: repo içine tek bayt ses yazılmaz.
    kok = repo_disinda(a.cikti or (KAYIT_KOKU / time.strftime("%Y%m%d-%H%M%S")))
    if kok.exists() and any(kok.iterdir()):
        raise ValueError(f"dizin bos degil, uzerine yazilmaz: {kok}")
    kok.mkdir(parents=True, exist_ok=True)

    import queue

    import numpy as np
    import sounddevice as sd

    belirtim = resolve_mic_device()
    aygit = select_input_device(belirtim)
    bilgi = (sd.query_devices(aygit) if aygit is not None
             else sd.query_devices(kind="input"))
    print(f"Aygit : {aygit!r}  {bilgi['name']}  (JARVIS_MIC_DEVICE -> {belirtim!r})")
    print(f"Kayit : {kok}   (repo DISINDA)")
    print(f"{len(CUMLELER)} cumle. Her birinde: Enter -> YARIM SANIYE BEKLE -> "
          "normal sesinle oku -> Enter.")

    kayitlar = []
    for no, cumle in enumerate(CUMLELER, 1):
        while True:
            print(f"\n[{no}/{len(CUMLELER)}]  {cumle}")
            input("  Enter: kaydi baslat ")
            kuyruk: "queue.Queue" = queue.Queue()

            def _geri_cagirma(indata, frames, time_info, status, _k=kuyruk):
                # Üretimle aynı: geri-çağırma, bloklayan read() DEĞİL
                # (voice/stt.py _default_chunk_source — bazı host API'lerinde
                # read() hata vermeden sıfır döndürüyor).
                _k.put(np.asarray(indata, dtype="float32").reshape(-1).copy())

            with sd.InputStream(samplerate=ORNEKLEME, channels=1, dtype="float32",
                                blocksize=PARCA, device=aygit,
                                callback=_geri_cagirma):
                input("  *** KAYITTA *** cumleyi oku, bitince Enter ")
            parcalar = []
            while not kuyruk.empty():
                parcalar.append(kuyruk.get())
            ornekler = (np.concatenate(parcalar) if parcalar
                        else np.zeros(0, dtype="float32"))
            ist = rms_istatistik(ornekler.tolist())
            print(f"  {len(ornekler) / ORNEKLEME:.1f} s | ortalama rms {ist['ortalama']:.5f}"
                  f" | tepe {ist['tepe']:.5f} | esik ({DEFAULT_SILENCE_THRESHOLD}) ustu"
                  f" %{ist['esik_ustu_yuzde']:.0f}")
            cevap = input("  Enter = tamam | t = tekrar kaydet | soyledigin metin "
                          "farkliysa onu yaz: ").strip()
            if cevap.lower() == "t":
                continue
            dosya = kok / f"cumle_{no:02d}.wav"
            _wav_yaz(dosya, ornekler)
            kayitlar.append({"no": no, "dosya": dosya.name, "okunacak": cumle,
                             "referans": cevap or cumle,
                             "sure_s": len(ornekler) / ORNEKLEME, **ist})
            # Her cümleden sonra yazılır: oturum yarıda kesilirse kaydedilen
            # cümleler kaybolmaz.
            (kok / "kayitlar.json").write_text(json.dumps(
                {"schema_version": 1, "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "aygit": {"indeks": aygit, "ad": bilgi["name"], "belirtim": belirtim},
                 "ornekleme": ORNEKLEME, "kayitlar": kayitlar},
                ensure_ascii=False, indent=2), encoding="utf-8")
            break

    print(f"\nBitti: {len(kayitlar)} kayit -> {kok}")
    print("Olcum icin: python scripts/olc_stt_turkce.py olc")
    return 0


# --------------------------------------------------------------------------- #
# olc — Kusur B taraması + Kusur A matrisi
# --------------------------------------------------------------------------- #

def _son_kayit() -> Path:
    adaylar = sorted(p for p in KAYIT_KOKU.glob("*") if (p / "kayitlar.json").exists())
    if not adaylar:
        raise FileNotFoundError(f"kayit bulunamadi: {KAYIT_KOKU} (once `kaydet`)")
    return adaylar[-1]


def _yaziya(model, ses, beam: int, hotwords: str | None = None,
            initial_prompt: str | None = None) -> str:
    # voice/stt.py FasterWhisperTranscriber.__call__ ile AYNI çağrı; yalnız
    # beam_size değişken. Segment üreteci burada tüketilir — çözümleme o an olur.
    # İpucu (KART_STT_HOTWORDS) yalnız VERİLDİĞİNDE geçer: verilmezse anahtar
    # hiç gönderilmez ve çağrı üretimle birebir aynı kalır. vad_filter kapanmaz.
    ipucu = {}
    if hotwords is not None:
        ipucu["hotwords"] = hotwords
    if initial_prompt is not None:
        ipucu["initial_prompt"] = initial_prompt
    segmentler, _bilgi = model.transcribe(ses, language="tr", beam_size=beam,
                                          vad_filter=True, **ipucu)
    return " ".join(s.text for s in segmentler).strip()


def _toplam_wer(satirlar: list) -> float:
    return (sum(s["hata"] for s in satirlar)
            / max(1, sum(s["kelime"] for s in satirlar)))


def olc(a) -> int:
    import os

    # Üretimle aynı: model önbellekten gelir, ağa çıkılmaz (config.py de
    # HF_*_OFFLINE yazıyor). Model yoksa gürültülü düşer, sessizce inmez.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    kok = repo_disinda(a.kayit or _son_kayit())
    meta = json.loads((kok / "kayitlar.json").read_text(encoding="utf-8"))
    sesler = [(k, _wav_oku(kok / k["dosya"])) for k in meta["kayitlar"]]
    print(f"Kayit: {kok} ({len(sesler)} cumle, aygit {meta['aygit']['ad']})")

    sonuc: dict = {"schema_version": 1, "kayit": str(kok),
                   "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "kusur_b": {}, "kusur_a": {}}

    # --- Kusur B: üretim kaydedicisi kayıt üzerinde ------------------------ #
    print("\n=== Kusur B — uretim kaydedicisi, sessizlik "
          f"{DEFAULT_SILENCE_DURATION_S} s ===")
    print("| esik | baslamayan | erken kesilen | tutulan/toplam (p50) |")
    print("|---|---|---|---|")
    uretim_kesimi = {}
    for esik in ESIKLER:
        sim = [sessizlik_simulasyonu(s.tolist(), esik) for _, s in sesler]
        sonuc["kusur_b"][str(esik)] = [
            {"no": k["no"], **d} for (k, _), d in zip(sesler, sim)]
        oran = [d["tutulan_s"] / d["toplam_s"] for d in sim if d["toplam_s"]]
        print(f"| {esik} | {sum(not d['basladi'] for d in sim)} | "
              f"{sum(d['erken_kesildi'] for d in sim)} | "
              f"{statistics.median(oran):.2f} |")
        if esik == DEFAULT_SILENCE_THRESHOLD:
            uretim_kesimi = {k["no"]: d for (k, _), d in zip(sesler, sim)}

    # --- Kusur A: model x beam matrisi ------------------------------------- #
    from faster_whisper import WhisperModel

    print("\n=== Kusur A — CPU/int8, isitma vakasi sayilmaz ===")
    print("| model | beam | WER | p50 ms | p90 ms | max ms | RTF p50 | yukleme s |")
    print("|---|---|---|---|---|---|---|---|")
    for model_adi in a.modeller.split(","):
        t0 = time.perf_counter()
        model = WhisperModel(model_adi, device="cpu", compute_type="int8")
        yukleme_s = time.perf_counter() - t0
        for beam in (int(b) for b in a.beamler.split(",")):
            _yaziya(model, sesler[0][1], beam)          # ısınma, sayılmaz
            satirlar = []
            for k, ses in sesler:
                t0 = time.perf_counter()
                metin = _yaziya(model, ses, beam)
                ms = (time.perf_counter() - t0) * 1000.0
                satirlar.append({"no": k["no"], "referans": k["referans"],
                                 "hipotez": metin, "ms": ms,
                                 "ses_s": len(ses) / ORNEKLEME,
                                 **wer(k["referans"], metin)})
            sureler = [s["ms"] for s in satirlar]
            ozet = {"wer": _toplam_wer(satirlar),
                    "p50_ms": statistics.median(sureler),
                    "p90_ms": _yuzdelik(sureler, 0.9), "max_ms": max(sureler),
                    "rtf_p50": statistics.median(
                        s["ms"] / 1000.0 / s["ses_s"] for s in satirlar),
                    "yukleme_s": yukleme_s, "satirlar": satirlar}
            sonuc["kusur_a"][f"{model_adi}/beam{beam}"] = ozet
            print(f"| {model_adi} | {beam} | {ozet['wer']:.3f} | {ozet['p50_ms']:.0f} | "
                  f"{ozet['p90_ms']:.0f} | {ozet['max_ms']:.0f} | "
                  f"{ozet['rtf_p50']:.2f} | {yukleme_s:.1f} |")

        # --- İkisinin arası: üretim kesmesi WER'e ne yaptı? (yalnız small/1) - #
        if model_adi == "small" and uretim_kesimi:
            kesik = []
            for k, ses in sesler:
                d = uretim_kesimi[k["no"]]
                if not d["basladi"]:
                    metin = ""                           # üretim hiç duymazdı
                else:
                    ilk = next(i for i, p in enumerate(_parcalar(ses)) if rms(p.tolist()) >= DEFAULT_SILENCE_THRESHOLD)
                    parca = ses[ilk * PARCA: ilk * PARCA + int(d["tutulan_s"] * ORNEKLEME)]
                    metin = _yaziya(model, parca, 1)
                kesik.append({"no": k["no"], "hipotez": metin,
                              **wer(k["referans"], metin)})
            sonuc["uretim_kesmesiyle_small_beam1"] = {
                "wer": _toplam_wer(kesik), "satirlar": kesik}
            print(f"\n  small/1, URETIM KESMESIYLE (esik {DEFAULT_SILENCE_THRESHOLD}): "
                  f"WER {_toplam_wer(kesik):.3f}  (tam kayit: "
                  f"{sonuc['kusur_a']['small/beam1']['wer']:.3f})")

    (kok / "olcum.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    print(f"\nHam sonuc (repo DISINDA): {kok / 'olcum.json'}")
    return 0


# --------------------------------------------------------------------------- #
# ipucu — KART_STT_HOTWORDS: small üzerinde hotwords / initial_prompt
# --------------------------------------------------------------------------- #

#: İpucu kayıtlardaki GERÇEK kelimelerden; uydurma kelime yok.
IPUCU_KELIMELER = ("Jarvis", "DeepSeek", "Ollama", "commit", "klima")


def ipucu(a) -> int:
    """small üzerinde ipucu matrisi: taban / hotwords / initial_prompt.

    Her ipucu satırı KENDİ tabanıyla cümle cümle karşılaştırılır. Önceki ölçüm
    dosyasına (olcum.json) dokunulmaz; sonuç olcum_ipucu.json'a yazılır.
    """
    import os

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    kok = repo_disinda(a.kayit or _son_kayit())
    meta = json.loads((kok / "kayitlar.json").read_text(encoding="utf-8"))
    sesler = [(k, _wav_oku(kok / k["dosya"])) for k in meta["kayitlar"]]
    # İki ipucu AYNI beş kelimeyi taşır; yalnız mekanizma farklıdır ve tek
    # satırda karıştırılmaz.
    hotwords = " ".join(IPUCU_KELIMELER)
    initial_prompt = ", ".join(IPUCU_KELIMELER) + "."
    tanimlar = (("small/1", 1, None, None),
                ("small/1+hotwords", 1, hotwords, None),
                ("small/5", 5, None, None),
                ("small/5+hotwords", 5, hotwords, None),
                ("small/1+initial_prompt", 1, None, initial_prompt))

    from faster_whisper import WhisperModel

    t0 = time.perf_counter()
    model = WhisperModel("small", device="cpu", compute_type="int8")
    sonuc: dict = {"schema_version": 1, "kayit": str(kok),
                   "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "hotwords": hotwords, "initial_prompt": initial_prompt,
                   "yukleme_s": time.perf_counter() - t0,
                   "satirlar": {}, "taban_denetimi": {}, "karsilastirma": {}}
    print(f"Kayit: {kok} ({len(sesler)} cumle) | hotwords={hotwords!r} | "
          f"initial_prompt={initial_prompt!r}")
    print("| satir | WER | hata | p50 ms | p90 ms | max ms |")
    print("|---|---|---|---|---|---|")
    for etiket, beam, hw, ip in tanimlar:
        _yaziya(model, sesler[0][1], beam, hotwords=hw, initial_prompt=ip)  # ısınma
        satirlar = []
        for k, ses in sesler:
            t0 = time.perf_counter()
            metin = _yaziya(model, ses, beam, hotwords=hw, initial_prompt=ip)
            satirlar.append({"no": k["no"], "referans": k["referans"],
                             "hipotez": metin,
                             "ms": (time.perf_counter() - t0) * 1000.0,
                             **wer(k["referans"], metin)})
        sureler = [s["ms"] for s in satirlar]
        ozet = {"wer": _toplam_wer(satirlar),
                "hata": sum(s["hata"] for s in satirlar),
                "p50_ms": statistics.median(sureler),
                "p90_ms": _yuzdelik(sureler, 0.9), "max_ms": max(sureler),
                "satirlar": satirlar}
        sonuc["satirlar"][etiket] = ozet
        print(f"| {etiket} | {ozet['wer']:.3f} | {ozet['hata']} | "
              f"{ozet['p50_ms']:.0f} | {ozet['p90_ms']:.0f} | {ozet['max_ms']:.0f} |")

    # Taban denetimi: ipucusuz satırlar önceki ölçümle (olcum.json) aynı mı?
    # Aynı değilse ölçüm düzeneği değişmiştir ve ipucu satırları yorumlanmaz.
    onceki = kok / "olcum.json"
    if onceki.exists():
        eski = json.loads(onceki.read_text(encoding="utf-8"))["kusur_a"]
        for etiket, eski_ad in (("small/1", "small/beam1"), ("small/5", "small/beam5")):
            e = {s["no"]: s["hipotez"] for s in eski[eski_ad]["satirlar"]}
            y = sonuc["satirlar"][etiket]
            farkli = [s["no"] for s in y["satirlar"] if s["hipotez"] != e.get(s["no"])]
            sonuc["taban_denetimi"][etiket] = {
                "wer": y["wer"], "onceki_wer": eski[eski_ad]["wer"], "metni_farkli": farkli}
            print(f"TABAN {etiket}: WER {y['wer']:.3f} (onceki {eski[eski_ad]['wer']:.3f})"
                  f" | metni farkli cumle: {farkli or 'yok'}")

    for ipuclu, taban in (("small/1+hotwords", "small/1"),
                          ("small/5+hotwords", "small/5"),
                          ("small/1+initial_prompt", "small/1")):
        k = karsilastir(sonuc["satirlar"][taban]["satirlar"],
                        sonuc["satirlar"][ipuclu]["satirlar"])
        sonuc["karsilastirma"][ipuclu] = k
        print(f"\n{ipuclu} vs {taban}: duzelen {len(k['duzelen'])} | bozulan "
              f"{len(k['bozulan'])} | metni degisen, hata ayni "
              f"{len(k['metni_degisen_ayni_hata'])}")
        for isaret, liste in (("+", k["duzelen"]), ("-", k["bozulan"]),
                              ("~", k["metni_degisen_ayni_hata"])):
            for d in liste:
                print(f"  {isaret} [{d['no']}] {d['once']} ({d['once_hata']}) -> "
                      f"{d['sonra']} ({d['sonra_hata']})")

    (kok / "olcum_ipucu.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nHam sonuc (repo DISINDA): {kok / 'olcum_ipucu.json'}")
    return 0


def main(argv=None) -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="STT Turkce sondasi (KART_STT_TURKCE)")
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kaydet", help="15 cumleyi mikrofondan kaydet (Ahmet)")
    k.add_argument("--cikti", type=Path, default=None,
                   help=f"kayit dizini, repo DISINDA (varsayilan: {KAYIT_KOKU}/<zaman>)")
    o = alt.add_parser("olc", help="Kusur B taramasi + Kusur A matrisi")
    o.add_argument("--kayit", type=Path, default=None,
                   help="kayit dizini (varsayilan: en yenisi)")
    o.add_argument("--modeller", default="small,medium")
    o.add_argument("--beamler", default="1,5")
    i = alt.add_parser("ipucu", help="small uzerinde hotwords / initial_prompt "
                                     "matrisi (KART_STT_HOTWORDS)")
    i.add_argument("--kayit", type=Path, default=None,
                   help="kayit dizini (varsayilan: en yenisi)")
    a = ap.parse_args(argv)
    return {"kaydet": kaydet, "olc": olc, "ipucu": ipucu}[a.komut](a)


if __name__ == "__main__":
    raise SystemExit(main())
