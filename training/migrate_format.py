"""Migrate old conversation format to new."""
import json
import shutil
from pathlib import Path
from datetime import datetime


CONV = Path("memory/conversations.json")


def migrate():
    if not CONV.exists():
        print("Yok"); return
    bk = CONV.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy(CONV, bk)
    print(f"💾 Yedek: {bk.name}")
    convs = json.loads(CONV.read_text(encoding='utf-8'))
    print(f"📊 Toplam: {len(convs)}\n")
    mig, new, skip = 0, 0, 0
    for conv in convs:
        if "messages" in conv and conv["messages"]:
            new += 1
            continue
        if "conversation" in conv:
            old = conv["conversation"]
            u = old.get("user", "").strip()
            a = old.get("assistant", "").strip()
            if not u or not a:
                skip += 1
                continue
            conv["messages"] = [
                {"role": "user", "content": u},
                {"role": "assistant", "content": a}
            ]
            if "metadata" not in conv:
                conv["metadata"] = {}
            if conv["metadata"].get("quality_score") is not None:
                conv["metadata"]["evaluated"] = True
                conv["metadata"]["eval_reason"] = conv["metadata"].get(
                    "feedback", "Manuel skor")
                conv["metadata"]["ts"] = conv.get("timestamp", "")
            mig += 1
            print(f"  ✅ {conv.get('id', '?')}")
        else:
            skip += 1
    CONV.write_text(json.dumps(convs, ensure_ascii=False, indent=2),
                    encoding='utf-8')
    print(f"\n✅ Çevrilen: {mig} | Yeni: {new} | Atlanan: {skip}")


if __name__ == "__main__":
    migrate()
