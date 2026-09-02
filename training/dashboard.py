"""Training Dashboard."""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter


CONV = Path("memory/conversations.json")
DATA = Path("training/train_data.jsonl")
MIN_Q = 7
TARGET = 50
EXCELLENT = 200


class C:
    R = '\033[91m'; G = '\033[92m'; Y = '\033[93m'; B = '\033[94m'
    M = '\033[95m'; CY = '\033[96m'; W = '\033[97m'
    BOLD = '\033[1m'; DIM = '\033[2m'; END = '\033[0m'


def bar(v, mx, w=30):
    if mx == 0:
        return ' ' * w
    return '█' * int(w * v / mx) + '░' * (w - int(w * v / mx))


def progress(cur, tgt, w=40):
    pct = min(100, int(100 * cur / tgt)) if tgt else 0
    return '█' * int(w * pct / 100) + '░' * (w - int(w * pct / 100)) + f" {pct}%"


def render():
    if not CONV.exists():
        print("Veri yok")
        return
    convs = json.loads(CONV.read_text(encoding='utf-8'))
    print()
    print(f"{C.CY}{C.BOLD}{'='*70}{C.END}")
    print(f"{C.CY}{C.BOLD}{'🤖 JARVIS DASHBOARD':^70}{C.END}")
    print(f"{C.CY}{C.BOLD}{'='*70}{C.END}")
    print(f"{C.DIM}{datetime.now().strftime('%Y-%m-%d %H:%M')}{C.END}\n")

    total = len(convs)
    ev = sum(1 for c in convs if c.get("metadata", {}).get("evaluated"))
    not_ev = total - ev
    hq = [c for c in convs
          if c.get("metadata", {}).get("quality_score", 0) >= MIN_Q]
    scores = [c.get("metadata", {}).get("quality_score", 0)
              for c in convs if c.get("metadata", {}).get("evaluated")]
    avg = sum(scores) / len(scores) if scores else 0

    print(f"{C.W}{C.BOLD}📊 GENEL{C.END}")
    print(f"  Toplam: {C.CY}{total}{C.END}  Değ: {C.G}{ev}{C.END}  "
          f"Bekleyen: {C.Y}{not_ev}{C.END}")
    print(f"  Ortalama: {C.M}{avg:.1f}/10{C.END}  "
          f"Kaliteli: {C.G}{C.BOLD}{len(hq)}{C.END}\n")

    print(f"{C.W}{C.BOLD}🎯 EĞİTİM HAZIRLIĞI{C.END}")
    print(f"  Min ({TARGET}): {progress(len(hq), TARGET)}")
    print(f"  Mükemmel ({EXCELLENT}): {progress(len(hq), EXCELLENT)}\n")

    if scores:
        print(f"{C.W}{C.BOLD}📈 KALİTE DAĞILIMI{C.END}")
        dist = Counter(scores)
        mx = max(dist.values())
        for s in range(10, 0, -1):
            cnt = dist.get(s, 0)
            col = C.G if s >= 7 else (C.Y if s >= 4 else C.R)
            print(f"  {col}{s:2d}/10{C.END} {bar(cnt, mx, 40)} {cnt}")
        print()

    if ev > 0:
        sc = sorted(
            [c for c in convs if c.get("metadata", {}).get("evaluated")],
            key=lambda c: c["metadata"].get("quality_score", 0), reverse=True)
        print(f"{C.W}{C.BOLD}⭐ EN İYİ 3{C.END}")
        for c in sc[:3]:
            s = c["metadata"].get("quality_score", 0)
            u = next((m["content"] for m in c["messages"] if m["role"]=="user"), "")[:50]
            a = next((m["content"] for m in c["messages"] if m["role"]=="assistant"), "")[:60]
            print(f"  {C.G}[{s}/10]{C.END} {C.DIM}{u}...{C.END}")
            print(f"         → {a}...")
        print()
        if len(sc) > 3:
            print(f"{C.W}{C.BOLD}⚠️  EN ZAYIF 3{C.END}")
            for c in sc[-3:]:
                s = c["metadata"].get("quality_score", 0)
                u = next((m["content"] for m in c["messages"] if m["role"]=="user"), "")[:50]
                rs = c["metadata"].get("eval_reason", "")[:60]
                print(f"  {C.R}[{s}/10]{C.END} {C.DIM}{u}...{C.END}")
                print(f"         ⚠ {rs}")
            print()

    if convs:
        try:
            ds = [c.get("metadata", {}).get("ts", "")[:10] for c in convs
                  if c.get("metadata", {}).get("ts")]
            dc = Counter(ds)
            recent = sorted(dc.items())[-7:]
            if recent:
                print(f"{C.W}{C.BOLD}📅 SON 7 GÜN{C.END}")
                mx = max(dc.values())
                for d, c in recent:
                    print(f"  {d}  {bar(c, mx, 30)} {c}")
                print()
        except:
            pass

    print(f"{C.W}{C.BOLD}💡 AKSİYON{C.END}")
    if not_ev > 0:
        print(f"  • {C.CY}python training/data_curator.py --once{C.END}")
    if len(hq) >= TARGET:
        print(f"  • {C.G}Eğitime hazır!{C.END}")
    print(f"\n{C.CY}{'='*70}{C.END}\n")


if __name__ == "__main__":
    try:
        render()
    except Exception as e:
        print(f"Hata: {e}")
