"""eval/run_turkish_quality.py — Türkçe kalite regresyon takımı, tek komut.

    python eval/run_turkish_quality.py                     # aktif local_main
    python eval/run_turkish_quality.py --model qwen2.5:7b
    python eval/run_turkish_quality.py --all-installed
    python eval/run_turkish_quality.py --category grounding

Neden var: 1621 testin hepsi **doğruluk** ölçüyor; kalite için tek bir ölçü
yoktu. Bir model/prompt/routing değişikliğinin iyileştirip iyileştirmediği
his ile değerlendiriliyordu. Bu takım o boşluğu kapatır — ama yalnız
**regresyonu** tutar: Türkçe akıcılığı Ahmet'in kulağı onaylar (FAZ-T1).

Tasarım: model çağrısı, VRAM ölçümü ve hafıza grafiği **enjekte edilebilir**.
Yavaş ve donanıma bağlı tek parça budur; ayrıldığı için koşucunun mantığı
Ollama olmadan test edilir (`tests/test_quality_runner.py`).

Her vaka **izole** çalışır: `seed_memory` geçici bir `LifeGraph`'a yüklenir,
zemin metni oradan üretilir, vaka bitince atılır. Bir vakanın olgusu
diğerine sızarsa "geri çağırma" testi anlamını yitirir.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from eval.quality_scorer import (  # noqa: E402
    exceeds_vram_ceiling,
    score_answer,
    turkish_equivalent_tps,
)

__all__ = ["run_suite", "write_report", "load_cases", "build_grounding",
           "DEFAULT_NUM_PREDICT"]

REPORT_SCHEMA_VERSION = 1
CASES_PATH = _REPO / "eval" / "turkish_quality_cases.json"
DEFAULT_OUT = _REPO / "automation"

#: Cevap butcesi (token). Vaka `num_predict` beyan ederse o gecerlidir.
#:
#: 2026-09-04 kiyasinda 10 kesilmenin **hepsi** bu sinira carpmisti; kesilme
#: modelin karari degil butcenin bitmesiydi ve "longform 0/4" bu yuzden
#: yaniltiyordu. Vaka "detayli anlat" derken kosucunun 400 token vermesi bir
#: olcum kusuruydu. Yalniz 4 longform vakasi daha genis butce beyan eder;
#: diger 60 vakanin kosulu hic degismedi (CLAUDE.md §3).
DEFAULT_NUM_PREDICT = 400

#: Kategori -> persona seviyesi. Kısa turlar L1, teknik L2, uzun anlatım L3.
_CATEGORY_LEVEL = {
    "tone": "L1", "mixed": "L1",
    "turkish": "L2", "technical": "L2", "memory": "L2", "grounding": "L2",
    "longform": "L3",
}


def load_cases(path: Path | str = CASES_PATH) -> List[Dict[str, Any]]:
    veri = json.loads(Path(path).read_text(encoding="utf-8"))
    return veri["cases"]


def build_grounding(seed_memory: Optional[Dict[str, Any]]) -> str:
    """`seed_memory`'yi geçici bir LifeGraph'a yükleyip zemin metni üretir.

    Boş/None ise **boş string** döner — kayıt yokken zemin verilmemeli, yoksa
    "uydurma testi" test olmaktan çıkar.
    """
    if not seed_memory:
        return ""

    from memory.entity_extractor import ExtractedFact
    from memory.life_graph import LifeGraph

    with tempfile.TemporaryDirectory() as gecici:
        kok = Path(gecici)
        kisiler = kok / "people.json"
        kisiler.write_text(
            json.dumps({"schema_version": 1,
                        "people": [{"id": "ahmet", "name": "Ahmet"}]},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        graf = LifeGraph(people_path=kisiler, events_path=kok / "events.jsonl")
        for iliski, nitelikler in seed_memory.items():
            for nitelik, deger in nitelikler.items():
                graf.remember(ExtractedFact(
                    category="family", relation=iliski, attribute=nitelik,
                    value=deger, raw_text=f"[eval seed] {iliski} {nitelik}: {deger}",
                    confidence=1.0,
                ))
        return graf.recall_context()


def run_suite(
    cases: List[Dict[str, Any]],
    ask: Callable[..., Dict[str, Any]],
    model: str,
    gpu_probe: Optional[Callable[[], Optional[float]]] = None,
    grounding_builder: Callable[[Optional[dict]], str] = build_grounding,
) -> Dict[str, Any]:
    """Vaka listesini koşturur ve puanlar.

    ``ask(model, prompt, level, system_extra)`` şu sözlüğü döndürmeli:
    ``{text, raw_tps, prompt_eval_ms, total_s}``. Hata fırlatabilir — koşu
    durmaz, hata vakanın kaydına yazılır.

    ``prompt_eval_ms`` **ilk token süresi değildir** (B11): Ollama'nın prompt
    değerlendirme süresidir. Gerçek uçtan uca gecikme
    ``scripts/olc_ses_gecikmesi.py`` ile ölçülür.
    """
    sonuclar: List[Dict[str, Any]] = []
    tepe_vram: Optional[float] = None

    for vaka in cases:
        seviye = _CATEGORY_LEVEL.get(vaka.get("category", ""), "L2")
        zemin = grounding_builder(vaka.get("seed_memory"))

        butce = int(vaka.get("num_predict") or DEFAULT_NUM_PREDICT)

        kayit: Dict[str, Any] = {
            "id": vaka.get("id"),
            "category": vaka.get("category"),
            "prompt": vaka.get("prompt"),
            "level": seviye,
            "grounded": bool(zemin.strip()),
            "num_predict": butce,
            # Ollama'nin durma sebebi: "length" butce bitti, "stop" model
            # kendi durdu. Olculmediyse None kalir -- uydurulmaz.
            "done_reason": None,
            "error": None,
        }

        try:
            cevap = ask(model, vaka["prompt"], seviye, system_extra=zemin,
                        num_predict=butce)
        except Exception as exc:  # noqa: BLE001 - koşu durmaz, kayda geçer
            kayit["error"] = f"{type(exc).__name__}: {exc}"
            kayit["answer"] = ""
            kayit["score"] = score_answer("", vaka)
            sonuclar.append(kayit)
            continue

        metin = (cevap or {}).get("text", "")
        kayit["answer"] = metin
        kayit["raw_tps"] = (cevap or {}).get("raw_tps")
        kayit["prompt_eval_ms"] = (cevap or {}).get("prompt_eval_ms")
        kayit["total_s"] = (cevap or {}).get("total_s")
        kayit["done_reason"] = (cevap or {}).get("done_reason")
        kayit["score"] = score_answer(metin, vaka)
        sonuclar.append(kayit)

        if gpu_probe is not None:
            try:
                simdi = gpu_probe()
                if simdi is not None:
                    tepe_vram = max(tepe_vram or 0, float(simdi))
            except Exception:  # noqa: BLE001 - ölçüm yoksa None kalır
                pass

    return {
        "model": model,
        "results": sonuclar,
        "summary": _summarise(sonuclar, tepe_vram),
    }


def _summarise(sonuclar: List[Dict[str, Any]],
               tepe_vram: Optional[float]) -> Dict[str, Any]:
    kategori: Dict[str, Dict[str, int]] = {}
    for r in sonuclar:
        k = kategori.setdefault(r["category"], {"passed": 0, "total": 0})
        k["total"] += 1
        if r["score"]["passed"]:
            k["passed"] += 1

    tps = [r["raw_tps"] for r in sonuclar if r.get("raw_tps")]
    ilk = [r["prompt_eval_ms"] for r in sonuclar if r.get("prompt_eval_ms")]
    ort_tps = sum(tps) / len(tps) if tps else None

    return {
        "passed": sum(1 for r in sonuclar if r["score"]["passed"]),
        "total": len(sonuclar),
        "errors": sum(1 for r in sonuclar if r["error"]),
        "by_category": kategori,
        "avg_raw_tps": ort_tps,
        "avg_turkish_tps": turkish_equivalent_tps(ort_tps) if ort_tps else None,
        "avg_prompt_eval_ms": sum(ilk) / len(ilk) if ilk else None,
        "peak_vram_mb": tepe_vram,
        "exceeds_vram_ceiling": exceeds_vram_ceiling(tepe_vram),
        # Ölçülemeyen sinyaller ayrıca sayılır: bunlar "kaldı" değil,
        # "bakılması gereken" demektir.
        "encoding_failures": sum(
            1 for r in sonuclar if not r["score"]["encoding_ok"]),
        # Uc evrensel dedektor (2026-09-03): bunlar RAPORLANIR ve ayrica
        # vakayi DUSURUR -- `encoding` gibi, `foreign_hits` gibi degil.
        "prompt_leaks": sum(1 for r in sonuclar if r["score"]["prompt_leak"]),
        "repetitions": sum(
            1 for r in sonuclar if not r["score"]["repetition_ok"]),
        # Esik 2 olsaydi kac vaka duserdi -- RAPORLANIR, puanlanmaz (A13).
        # Ikinci bir model olculdugunde takim yeniden kosturulmadan
        # karsilastirilabilsin diye tutulur.
        "repetitions_2x": sum(
            1 for r in sonuclar if r["score"]["repeated_phrase_2x"]),
        "truncations": sum(1 for r in sonuclar if r["score"]["truncated"]),
        # Kesilmenin SEBEBI artik tahmin degil olcum: "length" = butce bitti.
        "budget_exhausted": sum(
            1 for r in sonuclar if r.get("done_reason") == "length"),
        "truncations_budget": sum(
            1 for r in sonuclar
            if r["score"]["truncated"] and r.get("done_reason") == "length"),
        # Kusur 3: ikisi de artik PUANLANIYOR, sayilari yine de gorunur kalir.
        "foreign_sentences": sum(
            1 for r in sonuclar if not r["score"]["foreign_ok"]),
        "foreign_leaks": sum(1 for r in sonuclar if r["score"]["foreign_hits"]),
        "ai_boilerplate": sum(
            1 for r in sonuclar if r["score"]["ai_boilerplate"]),
        # Hitap RAPORLANIR, puanlanmaz: persona "her cumlede degil, dogal
        # dustugu yerde" diyor, yani tek bir cevapta zorunlu tutulamaz.
        "efendim_rate": sum(
            1 for r in sonuclar if r["score"]["has_efendim"]),
        # Kac vaka BEYAN EDILMIS bir iddia tasiyor? Gerisi yalniz evrensel
        # kontrollerden geciyor; "64/64" tek basina yaniltici olurdu.
        "declared_cases": sum(
            1 for r in sonuclar
            if any(r["score"][k] is not None for k in
                   ("grounding_ok", "contains_ok", "length_ok", "persona_ok"))),
    }


def write_report(sonuc: Dict[str, Any], out_dir: Path | str = DEFAULT_OUT,
                 stamp: Optional[str] = None) -> Dict[str, Path]:
    """Tarihli markdown tablosu + makine okunur JSON yan dosyası yazar."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M")
    guvenli = sonuc["model"].replace(":", "_").replace("/", "_")

    json_yolu = out_dir / f"KALITE_{guvenli}_{stamp}.json"
    json_yolu.write_text(json.dumps(
        {"schema_version": REPORT_SCHEMA_VERSION, "stamp": stamp, **sonuc},
        ensure_ascii=False, indent=2), encoding="utf-8")

    s = sonuc["summary"]
    satirlar = [
        f"# Türkçe Kalite Koşusu — `{sonuc['model']}`",
        "",
        f"Damga: `{stamp}` · Makine okunur: `{json_yolu.name}`",
        "",
        "> Bu tablo **regresyon** ölçer, akıcılık değil. Türkçe akıcılığı",
        "> Ahmet'in kulağı onaylar (FAZ-T1 deseni).",
        ">",
        "> **VRAM uyarısı:** `nvidia-smi` kartın **toplam** kullanımını verir,",
        "> yalnız bu modelinkini değil. Ekranda başka bir şey varsa değer",
        "> yüksek çıkar. Modeller arası karşılaştırma için aynı koşullarda",
        "> koşturulmalı; tek bir mutlak sayı olarak okunmamalı.",
        ">",
        "> **Oynaklık uyarısı — TEK KOŞU HÜKÜM DEĞİLDİR.** `temperature=0.2`",
        "> olmasına rağmen aynı model aynı vakalarda farklı sonuç verebiliyor;",
        "> ölçüldü (2026-09-01, llama3.1, grounding): **5/5, 5/5, 4/5**. Yani",
        "> bu takım şu hâliyle **sahte regresyon üretebilir** — bir sayı düştü",
        "> diye kod bozulmuş sanılmamalı. Regresyon birkaç koşunun **eğilimine**",
        "> bakılarak değerlendirilir. Kalıcı çözüm (N koşu ortalaması ya da",
        "> tolerans bandı) henüz kararlaştırılmadı:",
        "> `automation/AHMET_ONAYI_BEKLEYENLER.md` → A11.",
        "",
        f"**Geçen: {s['passed']}/{s['total']}**"
        + (f" · hata: {s['errors']}" if s["errors"] else ""),
        "",
        "> **Bu sayı bir kalite notu DEĞİL, bir regresyon tabanıdır.**",
        f"> {s['declared_cases']}/{s['total']} vaka beyan edilmiş iddia taşır",
        f"> (zemin, geri çağırma, uzunluk). Kalan {s['total'] - s['declared_cases']}",
        "> vaka yalnız evrensel kontrollerden geçer: kodlama bütünlüğü, boş",
        "> olmama, sistem prompt'u sızıntısı, tekrar, kesilme. Onların",
        "> `expected_elements` alanları serbest metindir ve Ahmet'in kulağı",
        "> için yazılmıştır — makineyle puanlanmaz.",
        ">",
        "> **Taban 2026-09-03'te değişti.** Üç evrensel dedektör (sızıntı /",
        "> tekrar / kesilme) eklendi ve uydurma kapsamı `technical`'a",
        "> genişletildi. Bu tarihten önceki raporların sayısıyla doğrudan",
        "> karşılaştırılamaz: ölçümün tanımı değişti, model değişmedi.",
        "",
        "| Kategori | Geçen |",
        "|---|---|",
    ]
    for k, v in sorted(s["by_category"].items()):
        satirlar.append(f"| {k} | {v['passed']}/{v['total']} |")

    satirlar += [
        "",
        "| Ölçüm | Değer |",
        "|---|---|",
        f"| Ortalama tok/s | {_g(s['avg_raw_tps'])} |",
        f"| Türkçe-eşdeğer tok/s | {_g(s['avg_turkish_tps'])} |",
        f"| Ortalama prompt degerlendirme | {_g(s['avg_prompt_eval_ms'], 'ms')} |",
        f"| Tepe VRAM (sistem geneli) | {_g(s['peak_vram_mb'], 'MB')} |",
        f"| VRAM tavanı aşıldı mı | {_bayrak(s['exceeds_vram_ceiling'])} |",
        f"| Bozuk kodlama | {s['encoding_failures']} |",
        f"| Sistem prompt'u sızıntısı | {s['prompt_leaks']} |",
        f"| Tekrar (dejenerasyon) | {s['repetitions']} |",
        f"| Tekrar 2× (raporlanır, puanlanmaz) | {s['repetitions_2x']}/{s['total']} |",
        f"| Kesilmiş cevap | {s['truncations']} |",
        f"| — bütçesi biten (done_reason=length) | {s['truncations_budget']} |",
        f"| — model kendi durdu | {s['truncations'] - s['truncations_budget']} |",
        f"| Bütçesi biten cevap (kesik olsun olmasın) | {s['budget_exhausted']} |",
        f"| İngilizce cümle sızıntısı (puanlanır) | {s['foreign_sentences']} |",
        f"| Yabancı kelime (raporlanır, puanlanmaz) | {s['foreign_leaks']} |",
        f"| Yapay zekâ kalıbı (puanlanır) | {s['ai_boilerplate']} |",
        f"| 'Efendim' hitabı (raporlanır, puanlanmaz) | {s['efendim_rate']}/{s['total']} |",
    ]

    kalanlar = [r for r in sonuc["results"] if not r["score"]["passed"]]
    if kalanlar:
        satirlar += ["", "## Kalan vakalar", "",
                     "| id | kategori | neden | cevap (ilk 70) |", "|---|---|---|---|"]
        for r in kalanlar:
            neden = ", ".join(r["score"]["failed_checks"]) or (r["error"] or "?")
            ozet = (r.get("answer") or "").replace("\n", " ")[:70]
            satirlar.append(f"| {r['id']} | {r['category']} | {neden} | {ozet} |")
    else:
        satirlar += ["", "Kalan vaka yok."]

    md_yolu = out_dir / f"KALITE_{guvenli}_{stamp}.md"
    md_yolu.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    return {"json": json_yolu, "markdown": md_yolu}


def _g(deger, birim: str = "") -> str:
    return "ölçülmedi" if deger is None else f"{deger:.1f}{birim}"


def _bayrak(deger) -> str:
    return {None: "ölçülmedi", True: "**EVET**", False: "hayır"}[deger]


# --------------------------------------------------------------------------- #
# Gerçek çalıştırıcılar
# --------------------------------------------------------------------------- #

def _ollama_ask(model: str, prompt: str, level: str,
                system_extra: Optional[str] = None,
                num_predict: int = DEFAULT_NUM_PREDICT) -> Dict[str, Any]:
    import urllib.request

    from agents.persona import build_system_prompt

    system = build_system_prompt(level=level)
    if system_extra and system_extra.strip():
        system += ("\n\n[BİLİNEN GERÇEKLER — yalnız bunlara dayan, "
                   f"burada olmayanı uydurma]\n{system_extra}")

    govde = json.dumps({
        "model": model, "prompt": prompt, "system": system, "stream": False,
        "keep_alive": "5m",
        "options": {"temperature": 0.2, "num_predict": num_predict,
                    "num_ctx": 4096},
    }).encode("utf-8")
    istek = urllib.request.Request(
        "http://localhost:11434/api/generate", data=govde,
        headers={"Content-Type": "application/json"}, method="POST")

    t0 = time.perf_counter()
    with urllib.request.urlopen(istek, timeout=300) as yanit:
        d = json.loads(yanit.read().decode("utf-8"))
    toplam = time.perf_counter() - t0

    sayi = d.get("eval_count") or 0
    sure_ns = d.get("eval_duration") or 1
    return {
        "text": (d.get("response") or "").strip(),
        "raw_tps": sayi / (sure_ns / 1e9) if sure_ns else 0.0,
        # B11: bu alan Ollama'nin `prompt_eval_duration` degeridir --
        # PROMPT DEGERLENDIRME suresi. "Ilk token" DEGIL: `stream=False`
        # kullandigimiz icin zaten "ilk token" diye bir an yok, cevap tek
        # parca geliyor. Eski adi (`first_token_ms`) karar verdirici bir
        # yanlisti; Turkish-Gemma bu sayiya bakilarak "TTFT 420 ms" diye
        # elendi -- sayi dogruydu, etiket yanlisti.
        # Gercek uctan uca gecikme hala OLCULMEDI; olcumu B12'nin konusu:
        # scripts/olc_ses_gecikmesi.py
        "prompt_eval_ms": (d.get("prompt_eval_duration") or 0) / 1e6,
        "total_s": toplam,
        # "length" = num_predict bitti, "stop" = model kendi durdu.
        "done_reason": d.get("done_reason"),
    }


def _nvidia_probe() -> Optional[float]:
    import subprocess
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=False)
        return float(r.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


def _installed_models() -> List[str]:
    import urllib.request
    d = json.loads(urllib.request.urlopen(
        "http://localhost:11434/api/tags", timeout=10).read())
    return [m["name"] for m in d.get("models", [])]


def main() -> int:
    ap = argparse.ArgumentParser(description="Türkçe kalite regresyon takımı")
    ap.add_argument("--model", help="tek model (varsayılan: aktif local_main)")
    ap.add_argument("--all-installed", action="store_true",
                    help="kurulu tüm modelleri sırayla koştur")
    ap.add_argument("--category", help="yalnız bu kategori")
    ap.add_argument("--limit", type=int, help="ilk N vaka (hızlı deneme)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()

    vakalar = load_cases()
    if a.category:
        vakalar = [c for c in vakalar if c.get("category") == a.category]
    if a.limit:
        vakalar = vakalar[:a.limit]
    if not vakalar:
        print("Eşleşen vaka yok.")
        return 1

    if a.all_installed:
        modeller = _installed_models()
    elif a.model:
        modeller = [a.model]
    else:
        from agents.model_registry import ModelRegistry
        modeller = [ModelRegistry().local_main()]

    for model in modeller:
        print(f"\n=== {model} · {len(vakalar)} vaka ===", flush=True)
        sonuc = run_suite(vakalar, _ollama_ask, model=model,
                          gpu_probe=_nvidia_probe)
        s = sonuc["summary"]
        yollar = write_report(sonuc, out_dir=a.out)
        print(f"  geçen {s['passed']}/{s['total']}"
              f" · {_g(s['avg_raw_tps'])} tok/s"
              f" · tepe VRAM {_g(s['peak_vram_mb'], 'MB')}", flush=True)
        print(f"  rapor: {yollar['markdown'].name}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
