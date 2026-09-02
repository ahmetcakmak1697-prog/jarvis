#!/usr/bin/env python3
"""
daily_report.py
JARVIS otonom inşa hattı için GÜNLÜK DURUM RAPORU.

Kaynaklar (hepsi makine durumu; elle yazılan handoff'a son):
    - roadmap_state.json   -> ne bitti, neredeyiz, ne kaldı, ne bloke
    - git log              -> bugün hangi commit'ler atıldı
    - .verifier/reports/*  -> son verdict'ler (PASS/FAIL/NEEDS_HUMAN)
    - cost_ledger.json     -> (opsiyonel) bugünkü token maliyeti

Çıktı: Markdown rapor (STDOUT + reports/daily_YYYYMMDD.md).
"GM" görünümü: en üstte "İMZANI BEKLEYEN" bölümü; gerisi detay.

Kullanım:
    python daily_report.py --repo . --state roadmap_state.json
23:59 zamanlaması (Windows Task Scheduler):
    schtasks /Create /SC DAILY /ST 23:59 /TN JarvisDailyReport ^
      /TR "python C:\\...\\daily_report.py --repo C:\\...\\jarvis-agent-auto --state C:\\...\\roadmap_state.json"
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _git_log_today(repo: Path, since: str) -> list[str]:
    cp = subprocess.run(
        ["git", "log", f"--since={since}", "--pretty=format:%h %s"],
        cwd=str(repo), capture_output=True, text=True)
    if cp.returncode != 0:
        return []
    return [ln for ln in cp.stdout.splitlines() if ln.strip()]


def _recent_verdicts(reports_dir: Path, limit: int = 20) -> list[dict]:
    if not reports_dir.exists():
        return []
    files = sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files[:limit]:
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
            if "verdict" in d:
                out.append({"file": f.name, "verdict": d.get("verdict"),
                            "task": d.get("contract_id") or d.get("task_id", "?"),
                            "at": d.get("timestamp", "")})
        except Exception:  # noqa: BLE001
            continue
    return out


def _eligible_next(steps: list[dict]) -> list[dict]:
    done = {s["id"] for s in steps if s.get("status") == "done"}
    todo = [s for s in steps if s.get("status") == "todo"]
    return [s for s in todo if all(dep in done for dep in s.get("depends_on", []))]


def _blocked(steps: list[dict]) -> list[tuple[dict, list[str]]]:
    done = {s["id"] for s in steps if s.get("status") == "done"}
    out = []
    for s in steps:
        if s.get("status") in ("todo", "blocked"):
            missing = [d for d in s.get("depends_on", []) if d not in done]
            if missing:
                out.append((s, missing))
    return out


def _needs_signature(steps: list[dict], verdicts: list[dict]) -> list[str]:
    sig = []
    for s in steps:
        st = s.get("status")
        ev = s.get("evidence", {}) or {}
        if st == "needs_human":
            reason = ev.get("reason") or (ev.get("reasons") or [""])[0]
            extra = f"  [review: {ev['review_branch']}]" if ev.get("review_branch") else ""
            sig.append(f"{s['id']} — {s.get('title','')} (needs_human: {reason}){extra}")
        elif st == "in_progress" and (
            s.get("autonomy") == "human_required"
            or s.get("kind") in ("architectural", "spec", "integration")
            or s.get("acceptance_criteria_human")):
            sig.append(f"{s['id']} — {s.get('title','')} (in_progress, {s.get('kind')})")
    for v in verdicts:
        if v.get("verdict") in ("FAIL", "NEEDS_HUMAN"):
            sig.append(f"verifier: {v['task']} -> {v['verdict']} ({v['file']})")
    return sig


def _today_cost(ledger: Optional[Path], since_date: str) -> Optional[float]:
    if not ledger or not ledger.exists():
        return None
    try:
        rows = json.loads(ledger.read_text(encoding="utf-8-sig"))
        return round(sum(float(r.get("usd", 0)) for r in rows
                         if str(r.get("date", "")).startswith(since_date)), 4)
    except Exception:  # noqa: BLE001
        return None


def build_report(repo: Path, state_path: Path, reports_dir: Path,
                 since: str, ledger: Optional[Path]) -> str:
    state = _load_state(state_path)
    steps = state.get("steps", [])
    counts = Counter(s.get("status", "?") for s in steps)
    total = len(steps) or 1
    done = counts.get("done", 0)
    pct = round(100 * done / total)

    since_date = since.split()[0]
    commits = _git_log_today(repo, since)
    verdicts = _recent_verdicts(reports_dir)
    eligible = _eligible_next(steps)
    blocked = _blocked(steps)
    signature = _needs_signature(steps, verdicts)
    cost = _today_cost(ledger, since_date)

    done_today = [s for s in steps
                  if s.get("status") == "done"
                  and str(s.get("evidence", {}).get("at", "")).startswith(since_date)]
    in_prog = [s for s in steps if s.get("status") == "in_progress"]

    L = []
    L.append(f"# JARVIS — Günlük Durum Raporu ({since_date})")
    L.append(f"İlerleme: **%{pct}** ({done}/{total} adım done)  ·  "
             f"in_progress: {counts.get('in_progress',0)}  ·  "
             f"todo: {counts.get('todo',0)}  ·  blocked: {len(blocked)}")
    if cost is not None:
        L.append(f"Bugünkü maliyet: **${cost}**")
    L.append("")

    L.append("## 🖊️ İMZANI BEKLEYEN")
    if signature:
        L += [f"- {x}" for x in signature]
    else:
        L.append("- Yok. Otonom hat temiz ilerliyor.")
    L.append("")

    L.append("## Bugün ne yapıldı")
    if done_today:
        L += [f"- ✔ {s['id']} — {s.get('title','')}" for s in done_today]
    if commits:
        L.append(f"- Commit'ler ({len(commits)}):")
        L += [f"    - {c}" for c in commits[:15]]
    if not done_today and not commits:
        L.append("- Kayda değer ilerleme yok.")
    L.append("")

    L.append("## Şu an nerede")
    if in_prog:
        for s in in_prog:
            L.append(f"- ⏳ {s['id']} — {s.get('title','')} ({s.get('kind')})")
    else:
        L.append("- Aktif in_progress adım yok.")
    L.append("")

    L.append("## Sıradaki uygun adımlar (bağımlılıkları tamam)")
    if eligible:
        for s in eligible[:8]:
            mode = "otonom" if (s.get("autonomy") == "auto"
                                and not s.get("acceptance_criteria_human")
                                and s.get("kind") in ("implement", "refactor")) else "imza gerekir"
            L.append(f"- {s['id']} — {s.get('title','')} [{mode}]")
    else:
        L.append("- Uygun adım yok (hepsi bloke veya bitti).")
    L.append("")

    if blocked:
        L.append("## Bloke (eksik bağımlılık)")
        for s, missing in blocked[:10]:
            L.append(f"- {s['id']} — bekliyor: {', '.join(missing)}")
        L.append("")

    L.append("## Son verifier verdict'leri")
    if verdicts:
        for v in verdicts[:8]:
            L.append(f"- {v['verdict']:11} {v['task']} ({v['file']})")
    else:
        L.append("- Kayıt yok.")
    L.append("")
    L.append(f"_Üretildi: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JARVIS günlük durum raporu")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--state", default="roadmap_state.json")
    ap.add_argument("--reports-dir", default=".verifier/reports")
    ap.add_argument("--since", default=None, help="git --since (varsayılan: bugün 00:00)")
    ap.add_argument("--cost-ledger", default=None)
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    state_path = Path(args.state)
    if not state_path.is_absolute():
        state_path = repo / state_path
    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = repo / reports_dir
    since = args.since or datetime.now().strftime("%Y-%m-%d 00:00")
    ledger = Path(args.cost_ledger) if args.cost_ledger else None

    report = build_report(repo, state_path, reports_dir, since, ledger)
    out_dir = reports_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    (out_dir / f"daily_{stamp}.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
