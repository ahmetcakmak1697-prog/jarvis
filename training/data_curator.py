"""Data Curator - night-time evaluation + JSONL export."""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from quality_evaluator import evaluate_batch


CONV = Path("memory/conversations.json")
DATA = Path("training/train_data.jsonl")
LOG = Path("logs/curator_log.txt")
MIN_Q = 7


def curate(verbose=True):
    if not CONV.exists():
        return {"total": 0, "evaluated": 0, "high_quality": 0}
    convs = json.loads(CONV.read_text(encoding='utf-8'))
    not_ev = sum(1 for c in convs
                 if not c.get("metadata", {}).get("evaluated"))
    if verbose:
        print(f"\n🌙 CURATION — {datetime.now().strftime('%H:%M')}")
        print(f"Toplam: {len(convs)} | Bekleyen: {not_ev}\n")
    if not_ev > 0:
        convs = evaluate_batch(convs, verbose=verbose)
        CONV.write_text(json.dumps(convs, ensure_ascii=False, indent=2),
                        encoding='utf-8')
    hq = sum(1 for c in convs
             if c.get("metadata", {}).get("quality_score", 0) >= MIN_Q)
    return {"total": len(convs),
            "evaluated": sum(1 for c in convs
                             if c.get("metadata", {}).get("evaluated")),
            "high_quality": hq}


def export_jsonl():
    if not CONV.exists():
        return 0
    convs = json.loads(CONV.read_text(encoding='utf-8'))
    DATA.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(DATA, 'w', encoding='utf-8') as f:
        for c in convs:
            sc = c.get("metadata", {}).get("quality_score", 0)
            if sc < MIN_Q:
                continue
            msgs = c.get("messages", [])
            u = next((m["content"] for m in msgs if m["role"] == "user"), "")
            a = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
            if u and a:
                row = {
                    "text": (
                        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                        f"Sen JARVIS'sin. Tony Stark'in Türkçe AI asistanı."
                        f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
                        f"{u}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
                        f"{a}<|eot_id|>"
                    ),
                    "score": sc
                }
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
                n += 1
    return n


def log(stats, exp):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*40}\n{datetime.now().isoformat()}\n"
                f"Toplam: {stats['total']} | Değ: {stats['evaluated']} | "
                f"Kal: {stats['high_quality']} | Exp: {exp}\n")


def run_once(verbose=True):
    stats = curate(verbose=verbose)
    exp = export_jsonl()
    if verbose:
        print(f"\n✅ DONE")
        print(f"Toplam: {stats['total']} | Değ: {stats['evaluated']} "
              f"| Kal(>={MIN_Q}): {stats['high_quality']} | Export: {exp}")
        if stats['high_quality'] >= 50:
            print(f"🎯 Eğitim için yeterli veri var!")
    log(stats, exp)
    return stats, exp


def schedule_nightly():
    try:
        import schedule
    except ImportError:
        print("pip install schedule")
        return
    import time
    schedule.every().day.at("02:00").do(lambda: run_once(True))
    print("🌙 Gece scheduler aktif (02:00). Ctrl+C ile durdur.")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--schedule", action="store_true")
    ap.add_argument("--export", action="store_true")
    a = ap.parse_args()
    if a.export:
        n = export_jsonl()
        print(f"✅ {n} satır → {DATA}")
    elif a.schedule:
        schedule_nightly()
    else:
        run_once(True)
