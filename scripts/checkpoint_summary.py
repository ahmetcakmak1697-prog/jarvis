#!/usr/bin/env python3
"""
checkpoint_summary.py
İMZA-ANI DURUM ÖZETİ.

Sistem durduğunda (imza kapısı / istendiğinde) son imzadan (checkpoint) bu yana
NE YAPILDIĞINI detaylı ve BAĞIMSIZ İNCELEMEYE HAZIR bir paket olarak çıkarır.
Sen bu paketi Claude (ben) + GPT + Gemini'ye verip kontrol ettirirsin; üçü de
"tamam" derse --sign ile checkpoint'i ilerletir ve sistemi devam ettirirsin.

Pencere = [son checkpoint commit'i] .. HEAD.
İmza atana (--sign) kadar pencere büyür; --sign marker'ı HEAD'e taşır.

Kullanım:
    python checkpoint_summary.py --repo . --state roadmap_state.json
    # paketi incele + Claude/GPT/Gemini'ye ver; üçü de onaylarsa:
    python checkpoint_summary.py --repo . --state roadmap_state.json --sign
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _git(repo: Path, *a: str) -> subprocess.CompletedProcess:
    cp = subprocess.run(["git", *a], cwd=str(repo), capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    cp.stdout = cp.stdout or ""
    cp.stderr = cp.stderr or ""
    return cp


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _root_commit(repo: Path) -> str:
    out = _git(repo, "rev-list", "--max-parents=0", "HEAD").stdout.split()
    return out[-1] if out else ""

def _commit_count(repo: Path, base: str) -> int:
    rng = f"{base}..HEAD" if base else "HEAD"
    out = _git(repo, "rev-list", "--count", rng).stdout.strip()
    return int(out) if out else 0


def _marker_file(reports_dir: Path) -> Path:
    return reports_dir.parent / "state" / "last_checkpoint.json"


def _load_marker(reports_dir: Path) -> dict:
    mf = _marker_file(reports_dir)
    if mf.exists():
        try:
            return json.loads(mf.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def _base_commit(repo: Path, marker: dict, full_history: bool) -> str:
    if marker.get("commit"):
        return marker["commit"]
    if full_history:
        return _root_commit(repo)
    return _head(repo)


TRUNCATED_NOTE = "Rapor k\u0131salt\u0131ld\u0131; tam diff i\u00e7in git komutlar\u0131n\u0131 kullan."


def _save_marker(reports_dir: Path, commit: str):
    mf = _marker_file(reports_dir)
    mf.parent.mkdir(parents=True, exist_ok=True)
    mf.write_text(json.dumps({"commit": commit,
                              "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
                  encoding="utf-8")


def _commits(repo: Path, base: str) -> list[list[str]]:
    rng = f"{base}..HEAD" if base else "HEAD"
    out = (_git(repo, "log", rng, "--pretty=format:%h\t%s\t%cI").stdout or "").splitlines()
    return [ln.split("\t") for ln in out if ln.strip()]


def _diffstat(repo: Path, base: str) -> str:
    rng = f"{base}..HEAD" if base else "HEAD"
    return _git(repo, "diff", "--stat", rng).stdout.strip()

def _diffstat_capped(repo: Path, base: str, max_lines: int = 120) -> str:
    rng = f"{base}..HEAD" if base else "HEAD"
    raw = _git(repo, "diff", "--stat", rng).stdout or ""
    if not raw.strip():
        return "(de\u011fi\u015fiklik yok)"
    d = raw.splitlines()
    if len(d) > max_lines:
        return "\n".join(d[:max_lines]) + f"\n... ({len(d)-max_lines} sat\u0131r daha kesildi; tam diffstat i\u00e7in: git diff --stat {rng})"
    return "\n".join(d)


def _diff_capped(repo: Path, base: str, max_lines: int = 500) -> str:
    rng = f"{base}..HEAD" if base else "HEAD"
    raw = _git(repo, "diff", rng).stdout or ""
    if not raw:
        return "(diff yok)"
    d = raw.splitlines()
    if len(d) > max_lines:
        return "\n".join(d[:max_lines]) + f"\n... ({len(d)-max_lines} satır daha kesildi; tam diff için ilgili commit'lere bak)"
    return "\n".join(d)


def _safe_print(text: str):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or sys.getdefaultencoding()
        sanitized = text.encode(enc, errors="replace").decode(enc, errors="replace")
        print(sanitized)


def build(
    repo: Path,
    state_path: Path,
    reports_dir: Path,
    ledger: Path | None,
    full_history: bool = False,
    max_commits: int = 30,
    max_diff_lines: int = 300,
    max_diffstat_lines: int = 120,
    max_report_chars: int = 120_000,
) -> str:
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    steps = state.get("steps", [])
    marker = _load_marker(reports_dir)
    base = _base_commit(repo, marker, full_history)
    no_marker = not marker
    commits = _commits(repo, base)
    win_short = {c[0] for c in commits}

    def _in_window(full_sha: str) -> bool:
        return bool(full_sha) and any(full_sha.startswith(s) for s in win_short)

    done_win = [s for s in steps if s.get("status") == "done"
                and _in_window(s.get("evidence", {}).get("commit", ""))]
    needs = [s for s in steps if s.get("status") == "needs_human"]

    # pencere içi FAIL/NEEDS_HUMAN verdict'leri (mtime marker dosyasından sonra)
    mtime0 = _marker_file(reports_dir).stat().st_mtime if _marker_file(reports_dir).exists() else 0
    fails = []
    if reports_dir.exists():
        for f in sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.stat().st_mtime < mtime0:
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                continue
            if d.get("verdict") in ("FAIL", "NEEDS_HUMAN"):
                fails.append((d.get("contract_id") or d.get("task_id", "?"), d.get("verdict"), f.name))

    cost = None
    if ledger and ledger.exists():
        try:
            rows = json.loads(ledger.read_text(encoding="utf-8-sig"))
            cost = round(sum(float(r.get("usd", 0)) for r in rows), 4)
        except Exception:  # noqa: BLE001
            cost = None

    total = len(steps) or 1
    done_total = sum(1 for s in steps if s.get("status") == "done")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    L = []
    L.append("# JARVIS \u2014 \u0130MZA-ANI CHECKPOINT \u00d6ZET\u0130")
    marker_at = marker.get("at", "-") if marker else "(yok \u2014 ilk \u00e7al\u0131\u015ft\u0131rma)"
    onceki = "\u00f6nceki"
    baslangic = "ba\u015flang\u0131\u00e7"
    L.append(f"Pencere: `{base[:10] or baslangic}` .. `HEAD ({_head(repo)[:10]})`  \u00b7  "
             f"{onceki} imza: {marker_at}")
    L.append(f"Genel ilerleme: %{round(100*done_total/total)} ({done_total}/{total})  \u00b7  "
             f"bu pencerede {len(done_win)} ad\u0131m tamamland\u0131, {len(commits)} commit"
             + (f"  \u00b7  maliyet ${cost}" if cost is not None else ""))
    if no_marker and not full_history:
        L.append("")
        daha_once = "Daha \u00f6nce"
        yalnizca = "yaln\u0131zca"
        olusturulmus = "olu\u015fturulmu\u015ftur"
        gormek = "g\u00f6rmek"
        icin = "i\u00e7in"
        L.append(f"> **Not:** {daha_once} checkpoint i\u015faretlenmemi\u015f. Bu rapor {yalnizca} mevcut HEAD")
        L.append(f"> baz al\u0131narak {olusturulmus} (tarih\u00e7e yok). Ge\u00e7mi\u015fin tamam\u0131n\u0131 {gormek} {icin}")
        L.append("> `--full-history` kullan\u0131n.")
    L.append("")

    L.append("## 🖊️ İMZANI BEKLEYEN (karar gerektiren)")
    if needs:
        for s in needs:
            ev = s.get("evidence", {}) or {}
            reason = ev.get("reason") or (ev.get("reasons") or [""])[0]
            br = f"  → değişiklik dalı: `{ev['review_branch']}`" if ev.get("review_branch") else ""
            L.append(f"- **{s['id']}** — {s.get('title','')}  ({reason}){br}")
    else:
        L.append("- Yok.")
    L.append("")

    L.append("## ✅ Bu pencerede tamamlananlar (otonom, kapıdan geçti)")
    if done_win:
        for s in done_win:
            ev = s.get("evidence", {})
            L.append(f"- {s['id']} — {s.get('title','')}  (commit `{ev.get('commit','')[:10]}`, verdict {ev.get('verdict','?')})")
    else:
        L.append("- Yok.")
    L.append("")

    if fails:
        L.append("## ⚠️ Bu pencerede başarısızlık / geri alma")
        for tid, v, fn in fails[:15]:
            L.append(f"- {tid} -> {v} ({fn})")
        L.append("")

    L.append("## Commit'ler")
    if commits:
        for sh, msg, when in commits[:max_commits]:
            L.append(f"- `{sh}` {msg}  ({when[:16]})")
        if len(commits) > max_commits:
            L.append(f"... ({len(commits) - max_commits} commit daha; tam liste i\u00e7in: git log {base}..HEAD --oneline)")
    else:
        L.append("- (pencerede commit yok)")
    L.append("")

    L.append("## Diffstat (pencere)")
    ds = _diffstat_capped(repo, base, max_diffstat_lines)
    L.append("```\n" + ds + "\n```")
    L.append("")

    L.append("## 🔍 BAĞIMSIZ İNCELEME PAKETİ (Claude / GPT / Gemini'ye verilecek)")
    L.append("Aşağıdaki diff'i incele ve şu sorulara ayrı ayrı yanıt ver:")
    L.append("1. Yapılan değişiklik, ilgili adımın hedefini gerçekten karşılıyor mu, yoksa sadece testten mi geçiyor?")
    L.append("2. Atlanan/yarım kalan bir şey var mı? (edge-case, hata yolu, sayısal/istatistiksel doğruluk)")
    L.append("3. Gizli risk var mı? (yan etki, geriye dönük uyumluluk, güvenlik, performans)")
    L.append("4. Testler bu değişikliği gerçekten doğruluyor mu? (zayıf assert / eksik kapsam)")
    L.append("5. İmzalanmalı mı, yoksa düzeltilecek nokta var mı? (net karar)")
    L.append("")
    L.append("```diff\n" + (_diff_capped(repo, base, max_diff_lines) or "(diff yok)") + "\n```")
    L.append("")
    raw = "\n".join(L) + "\n"
    truncated = False
    if len(raw) > max_report_chars:
        raw = raw[:max_report_chars]
        raw += f"\n\n---\n{TRUNCATED_NOTE}\n"
        truncated = True
    if not truncated:
        raw += f"\n\n_Üretildi: {now}_"
    else:
        raw += f"_Üretildi: {now}_"
    return raw


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JARVIS imza-anı checkpoint özeti")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--state", default="roadmap_state.json")
    ap.add_argument("--reports-dir", default=".verifier/reports")
    ap.add_argument("--cost-ledger", default=None)
    ap.add_argument("--sign", action="store_true",
                    help="İncelemeler onayladıysa: checkpoint'i HEAD'e ilerlet + roadmap_state commit'le")
    ap.add_argument("--full-history", action="store_true",
                    help="İlk çalıştırmada tüm geçmişi göster (varsayılan: sadece HEAD)")
    ap.add_argument("--max-commits", type=int, default=30)
    ap.add_argument("--max-diff-lines", type=int, default=300)
    ap.add_argument("--max-diffstat-lines", type=int, default=120)
    ap.add_argument("--max-report-chars", type=int, default=120000)
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    state_path = repo / args.state if not Path(args.state).is_absolute() else Path(args.state)
    reports_dir = repo / args.reports_dir if not Path(args.reports_dir).is_absolute() else Path(args.reports_dir)
    ledger = Path(args.cost_ledger) if args.cost_ledger else None
    reports_dir.mkdir(parents=True, exist_ok=True)

    if args.sign:
        _git(repo, "add", "--", str(state_path))
        if _git(repo, "diff", "--cached", "--quiet").returncode != 0:
            _git(repo, "commit", "-m",
                 f"checkpoint signed: roadmap_state @ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        _save_marker(reports_dir, _head(repo))
        print(f"İmzalandı. Checkpoint ilerletildi -> {_head(repo)[:10]}. Sistem devam edebilir.")
        return 0

    report = build(
        repo=repo,
        state_path=state_path,
        reports_dir=reports_dir,
        ledger=ledger,
        full_history=args.full_history,
        max_commits=args.max_commits,
        max_diff_lines=args.max_diff_lines,
        max_diffstat_lines=args.max_diffstat_lines,
        max_report_chars=args.max_report_chars,
    )
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out = reports_dir / f"checkpoint_{stamp}.md"
    out.write_text(report, encoding="utf-8")
    _safe_print(report)
    print(f"\n[Özet yazıldı: {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
