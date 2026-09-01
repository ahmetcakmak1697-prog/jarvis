#!/usr/bin/env python3
"""
orchestrator.py
JARVIS otonom inşa beyni (SCAFFOLD).

Döngü (her uygun adım için):
    roadmap_state oku -> sıradaki eligible adımı seç
    -> task dosyası + outcome contract üret
    -> [spec-by-test] implement adımında tests/ allowed_paths'ten çıkarılır
    -> checkpoint al (geri dönüş noktası)
    -> jarvis_auto_task.ps1 çağır (OpenCode/DeepSeek + verifier + repair; AUTO-COMMIT YOK)
    -> verifier verdict + diff istatistiği oku
    -> escalation_policy ile karar ver
    -> PROCEED_COMMIT: sadece izinli yolları commit'le (push YOK)
       HUMAN_GATE   : değişikliği review/<id> dalına park et, ana dalı temizle, imza bekle
       HALT         : checkpoint'e geri sar, dur
    -> roadmap_state güncelle, log yaz
    sonra: daily_report üret

GÜVENLİK VARSAYILANLARI (kasıtlı):
    * DRY-RUN varsayılan. Gerçek çalışma için: --arm VE --budget zorunlu.
    * acceptance_criteria_machine BOŞ olan 'auto' adım ASLA otonom koşmaz -> human_gate.
    * implement/refactor adımında maker tests/ göremez (spec-by-test).
    * commit yalnızca contract'taki allowed_paths; asla 'git add -A'; asla push.
    * her koşum --max-steps ile sınırlı; bütçe aşımında HALT.

Bu hiçbir adımı 'doğru' yapmaz; sadece mekanik adımları güvenli sınırlarda ilerletir.
Yargı adımları (mimari/spec/integration/insan-kriteri/hassas alan) sana gelir.

Hızlı görüş (hiçbir şey değiştirmez):
    python orchestrator.py --repo . --state roadmap_state.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# escalation_policy aynı klasörden
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from escalation_policy import Decision, DiffStats, PolicyConfig, Step, decide
except Exception as e:  # noqa: BLE001
    print(f"HATA: escalation_policy import edilemedi: {e}")
    raise

TEST_GLOBS_PREFIXES = ("tests/", "test/")


# --------------------------------------------------------------------------- #
# git yardımcıları
# --------------------------------------------------------------------------- #

def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _is_clean(repo: Path, ignore: tuple = ()) -> bool:
    """Kaynak ağacı temiz mi? Orchestrator'ın kendi defter/runtime dosyaları
    (roadmap_state, active contract, .verifier, TASK_*, cost_ledger) sayılmaz."""
    lines = [l for l in _git(repo, "status", "--porcelain").stdout.splitlines() if l.strip()]
    def ignored(path: str) -> bool:
        p = path.replace("\\", "/")
        return any(tok in p for tok in ignore)
    return all(ignored(l[3:]) for l in lines)


def _diff_stats(repo: Path, base: str) -> DiffStats:
    names = [l.strip() for l in _git(repo, "diff", "--name-only", base).stdout.splitlines() if l.strip()]
    names += [l.strip() for l in _git(repo, "ls-files", "--others", "--exclude-standard").stdout.splitlines() if l.strip()]
    names = sorted(set(n for n in names if "__pycache__/" not in n and not n.endswith((".pyc", ".pyo"))))
    deletions = 0
    for line in _git(repo, "diff", "--numstat", base).stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[1].isdigit():
            deletions += int(parts[1])
    files_deleted = len([l for l in _git(repo, "diff", "--diff-filter=D", "--name-only", base).stdout.splitlines() if l.strip()])
    return DiffStats(files_changed=len(names), deletions=deletions,
                     files_deleted=files_deleted, changed_paths=names)


def _path_matches(path: str, globs: list) -> bool:
    import fnmatch
    p = path.replace("\\", "/")
    for g in globs:
        gg = g.replace("\\", "/")
        if fnmatch.fnmatch(p, gg):
            return True
        if gg.startswith("**/") and fnmatch.fnmatch(p, gg[3:]):
            return True
        prefix = gg.rstrip("*").rstrip("/")
        if prefix and (p == prefix or p.startswith(prefix + "/")):
            return True
    return False


# Orchestrator'ın ürettiği, temizlenmesi güvenli runtime yolları (global clean YOK).
_RUNTIME_CLEAN = [".verifier/tasks", "outcome_contract.active.json", "TASK_*.md"]
# Commit/temiz-ağaç hesabında "kaynak değil, defter" sayılan dosyalar.
_RUNTIME_TOKENS = (".verifier/", "outcome_contract.active.json", "cost_ledger.json",
                   "TASK_", "roadmap_state.json")


def _scoped_clean(repo: Path, allowed: tuple = ()):
    """Untracked'ı YALNIZCA runtime + allowed kapsamında temizle (global -fd YOK)."""
    paths = list(_RUNTIME_CLEAN) + list(allowed)
    if paths:
        _git(repo, "clean", "-fd", "--", *paths)


def _rollback(repo: Path, checkpoint: str, allowed: tuple = ()):
    """Tracked değişiklikleri checkpoint'e sar; untracked'ı yalnızca runtime + allowed
    kapsamında temizle. Kapsam dışı untracked dosya yerinde kalır -> bir sonraki
    temiz-ağaç kontrolünde HALT olarak yüzeye çıkar (sessizce kaybolmaz)."""
    _git(repo, "reset", "--hard", checkpoint)
    _scoped_clean(repo, allowed)


def _park_to_review(repo: Path, checkpoint: str, step_id: str, allowed: list, msg: str) -> str:
    """Uncommitted değişiklikleri review/<id> dalına commit'le, ana dalı checkpoint'e sar.
    Eğer commit başarısız olursa boş string döndür (çağıran HUMAN_GATE/HALT kararını versin).
    Temizlik KAPSAMLI -- global git clean YOK (ilgisiz untracked dosya silinmez)."""
    for p in allowed:
        _git(repo, "add", "--", p)
    cp = _git(repo, "commit", "-m", msg)
    if cp.returncode != 0:
        return ""
    branch = f"review/{step_id}"
    _git(repo, "branch", "-f", branch)
    _git(repo, "reset", "--hard", checkpoint)
    _scoped_clean(repo, tuple(allowed))
    return branch


def _is_forbidden(path: str, globs: list[str]) -> bool:
    import fnmatch
    p = path.replace("\\", "/")
    for g in globs:
        gg = g.replace("\\", "/")
        if fnmatch.fnmatch(p, gg):
            return True
        if gg.startswith("**/") and fnmatch.fnmatch(p, gg[3:]):  # kök dosya da yakalansın
            return True
        prefix = gg.rstrip("*").rstrip("/")  # "memory/**" -> "memory/"
        if prefix and (p == prefix or p.startswith(prefix + "/")):
            return True
    return False


def _safe_commit(repo: Path, allowed: list[str], forbidden: list[str], msg: str) -> tuple[bool, str]:
    lines = [l for l in _git(repo, "status", "--porcelain").stdout.splitlines() if l.strip()]
    # porcelain: "XY PATH" -> path index 3'ten başlar (satırı strip ETME). Rename: "old -> new".
    def _path(l: str) -> str:
        p = l[3:].strip()
        return p.split(" -> ")[-1] if " -> " in p else p
    changed_paths = [_path(l) for l in lines]
    # Yasak yol?
    for p in changed_paths:
        if _is_forbidden(p, forbidden):
            return False, f"Yasak yol commit'e girecekti: {p}"
    # Kapsam dışı KAYNAK değişikliği? (defter/runtime dosyaları hariç) -> kısmi commit YOK.
    out_of_scope = [p for p in changed_paths
                    if not _path_matches(p, allowed)
                    and not any(tok in p.replace("\\", "/") for tok in _RUNTIME_TOKENS)]
    if out_of_scope:
        return False, ("Kapsam dışı kaynak değişikliği (kısmi commit reddedildi): "
                       + ", ".join(out_of_scope[:5]))
    for p in allowed:
        _git(repo, "add", "--", p)  # ASLA -A
    if _git(repo, "diff", "--cached", "--quiet").returncode == 0:
        return False, "Stage edilecek (izinli) değişiklik yok."
    cp = _git(repo, "commit", "-m", msg)  # push YOK
    return (cp.returncode == 0, cp.stdout + cp.stderr)


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #

def _load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_state(path: Path, state: dict):
    state["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _select_next(steps: list[dict]) -> Optional[dict]:
    done = {s["id"] for s in steps if s.get("status") == "done"}
    for s in steps:  # dosya sırası = roadmap sırası -> "atlama yok"
        if s.get("status") == "todo" and all(d in done for d in s.get("depends_on", [])):
            return s
    return None


# --------------------------------------------------------------------------- #
# task + contract üretimi (DeepSeek'e giden odaklı brief)
# --------------------------------------------------------------------------- #

def _strip_tests(paths: list[str]) -> list[str]:
    return [p for p in paths if not p.replace("\\", "/").startswith(TEST_GLOBS_PREFIXES)
            and "tests/" not in p.replace("\\", "/")]


def _is_judgment(step: dict) -> bool:
    return (step.get("kind") in ("architectural", "spec", "integration")
            or step.get("autonomy") == "human_required"
            or bool(step.get("acceptance_criteria_human")))


def _has_correctness_gates(step: dict) -> bool:
    criteria = [c.lower() for c in step.get("acceptance_criteria_machine", [])]
    has_reference = any("reference" in c or "oracle" in c or "onaylı çıktı" in c or "known output" in c for c in criteria)
    has_property = any("property" in c or "invariant" in c for c in criteria)
    has_mutation = any("mutation" in c or "error-injection" in c or "error injection" in c for c in criteria)
    return has_reference and has_property and has_mutation


def _is_executable_criterion(text: str) -> bool:
    """Heuristic: if text starts with a known command pattern, treat as executable."""
    known_prefixes = ("pytest", "py ", "ruff", "mypy", "flake8", "black", "isort",
                      "pytest::")
    return text.strip().lower().startswith(known_prefixes)


def _criterion_to_command(text: str) -> str:
    """Convert a machine criterion to a shell command string."""
    t = text.strip()
    if t.startswith("pytest::"):
        return "py -3.11 -m pytest " + t[len("pytest::"):].strip()
    return t


def _gen_contract(step: dict) -> dict:
    allowed = list(step.get("allowed_paths", []))
    if step.get("kind") in ("implement", "refactor"):
        allowed = _strip_tests(allowed)  # spec-by-test

    machine_criteria = list(step.get("acceptance_criteria_machine", []))
    human_criteria = list(step.get("acceptance_criteria_human", []))

    required_commands = []
    machine_notes = []
    for c in machine_criteria:
        if _is_executable_criterion(c):
            required_commands.append(_criterion_to_command(c))
        else:
            machine_notes.append(c)

    notes_parts = list(step.get("notes", "").splitlines()) if step.get("notes") else []
    if machine_notes:
        notes_parts.append("Non-executable machine criteria: " + "; ".join(machine_notes))
    if human_criteria:
        notes_parts.append("Human criteria: " + "; ".join(human_criteria))

    minimum_pytest = step.get("minimum_pytest_collected")
    if minimum_pytest is None:
        minimum_pytest = 0  # safe default from example template

    notes_text = "\n".join(notes_parts).strip()

    return {
        "schema_version": 1,
        "task_id": step["id"],
        "goal": step.get("title", ""),
        "allowed_paths": allowed,
        "forbidden_paths": [".env", ".env.*", "**/.env", "**/secrets/**",
                            "**/*.pem", "**/id_rsa", "**/id_ed25519", "memory/**"],
        "required_commands": required_commands,
        "minimum_pytest_collected": minimum_pytest,
        "human_review_required": _is_judgment(step),
        "notes": notes_text,
    }


def _gen_task_md(step: dict, contract: dict) -> str:
    no_test = step.get("kind") in ("implement", "refactor")
    L = [
        f"# TASK: {step['id']} — {step.get('title','')}",
        "",
        "## Hedef",
        step.get("title", ""),
        step.get("notes", ""),
        "",
        "## Dokunabileceğin dosyalar (allowed_paths)",
    ]
    L += [f"- {p}" for p in contract["allowed_paths"]] or ["- (yok — bu adım yanlış yapılandırılmış)"]
    if no_test:
        L += ["", "## KESİN KURAL: tests/ DEĞİŞTİRME",
              "Bu bir implement adımı. Testler dondurulmuş spec'tir; sadece kodu yaz.",
              "Testleri geçirmek için testi değil kodu düzelt."]
    L += ["", "## Geçmesi gereken kriterler"]
    L += [f"- {c}" for c in step.get("acceptance_criteria_machine", [])] or ["- pytest, ruff"]
    L += ["", "## Dokunamayacağın yollar", "- .env, secrets/, memory/, *.pem, anahtarlar",
          "", "## Başarısızsa", "Repair round yap; testleri zayıflatma/silme."]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# runner çağrısı (armed)
# --------------------------------------------------------------------------- #

def _runner_cmd(runner: Path, task_file: Path, max_rounds: int, contract_path: Path) -> list[str]:
    # AUTO-COMMIT YOK: commit kararını orchestrator verir (eskalasyondan sonra).
    # ContractPath: runner verifier'ı bu contract ile koşmalı (orchestrator'ın yazdığı).
    args = ["-TaskFile", str(task_file), "-MaxRounds", str(max_rounds),
            "-ContractPath", str(contract_path)]
    if platform.system() == "Windows":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(runner), *args]
    return ["pwsh", "-File", str(runner), *args]


def _read_verdict(reports_dir: Path, task_id: str, min_mtime: float) -> str:
    """Strict report reading: accept ONLY the exact report filename produced by
    verifier_runner.py, check it is fresh (mtime >= min_mtime), and task_id matches.
    No latest-report fallback. If missing -> FAIL."""
    report_file = reports_dir / f"verifier_report_{task_id}.json"
    if not report_file.exists():
        return "FAIL"
    if report_file.stat().st_mtime < min_mtime - 1:
        return "FAIL"
    try:
        d = json.loads(report_file.read_text(encoding="utf-8-sig"))
        if d.get("task_id") == task_id:
            v = d.get("verdict")
            if v in ("PASS", "FAIL", "NEEDS_HUMAN"):
                return v
        return "FAIL"
    except Exception:  # noqa: BLE001
        return "FAIL"


def _cost_so_far(ledger: Optional[Path]) -> float:
    if not ledger or not ledger.exists():
        return 0.0
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        rows = json.loads(ledger.read_text(encoding="utf-8-sig"))
        return round(sum(float(r.get("usd", 0)) for r in rows
                         if str(r.get("date", "")).startswith(today)), 4)
    except Exception:  # noqa: BLE001
        return 0.0


# --------------------------------------------------------------------------- #
# bir adım döngüsü
# --------------------------------------------------------------------------- #

def run_cycle(step: dict, repo: Path, state_path: Path, state: dict, reports_dir: Path,
              runner: Path, contract_path: Path, task_dir: Path, cfg: PolicyConfig,
              cost_ledger: Optional[Path], armed: bool, log: list[str]) -> str:
    sid = step["id"]
    contract = _gen_contract(step)
    task_md = _gen_task_md(step, contract)

    # --- Güvenlik önkapıları (armed olsun ya da olmasın mantık aynı) ---
    if step.get("autonomy") == "auto" and not step.get("acceptance_criteria_machine"):
        log.append(f"{sid}: auto ama machine kriteri yok -> human_required'e çevriliyor.")
        step["autonomy"] = "human_required"
    if step.get("kind") in ("implement", "refactor") and not contract["allowed_paths"]:
        log.append(f"{sid}: implement ama (tests çıkınca) allowed_paths boş -> HUMAN_GATE (yanlış yapılandırma).")
        step["status"] = "needs_human"
        step.setdefault("evidence", {})["reason"] = "allowed_paths boş"
        return "HUMAN_GATE"

    sp = StepPlan(sid, contract, task_md)
    judgment = _is_judgment(step)

    if not armed:
        log.append(f"[DRY-RUN] {sid} ({step.get('kind')}, autonomy={step.get('autonomy')})")
        log.append(f"          allowed (tests çıkmış): {contract['allowed_paths']}")
        log.append(f"          human_review_required: {contract['human_review_required']}")
        if judgment:
            log.append("          -> yargı adımı: maker ATLANIR, doğrudan HUMAN_GATE.")
        else:
            log.append(f"          runner: {' '.join(_runner_cmd(runner, task_dir / f'TASK_{sid}.md', cfg.max_repair_rounds, contract_path))}")
        return "DRY_RUN"

    # --- ARMED ---
    if judgment:
        step["status"] = "needs_human"
        step.setdefault("evidence", {}).update(
            {"verdict": "—", "reason": "yargı adımı: maker atlandı, doğrudan imza",
             "at": datetime.now().strftime("%Y-%m-%d")})
        log.append(f"{sid}: yargı adımı -> maker çalıştırılmadı, imzanı bekliyor.")
        return "HUMAN_GATE"

    if not _is_clean(repo, ignore=(state_path.name, contract_path.name, ".verifier/",
                                   "TASK_", "cost_ledger")):
        log.append(f"{sid}: çalışma ağacı (kaynak) kirli, başlamadan dur. (önce temizle)")
        return "HALT"
    checkpoint = _head(repo)
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"TASK_{sid}.md"
    task_file.write_text(task_md, encoding="utf-8")
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")

    run_start = time.time()
    cp = subprocess.run(_runner_cmd(runner, task_file, cfg.max_repair_rounds, contract_path),
                        cwd=str(repo), capture_output=True, text=True)
    runner_ok = cp.returncode == 0
    # Repair runner'ın işi (MaxRounds); orchestrator AYNI adımı tekrar koşturmaz.
    verdict = _read_verdict(reports_dir, sid, run_start) if runner_ok else "FAIL"
    if not runner_ok:
        log.append(f"{sid}: runner exit={cp.returncode} -> FAIL (OpenCode/verifier başarısız).")

    diff = _diff_stats(repo, checkpoint)
    cost = _cost_so_far(cost_ledger)
    decision, reasons = decide(Step(sid, step.get("kind", "implement"),
                                    step.get("autonomy", "auto"),
                                    step.get("acceptance_criteria_human", [])),
                               verdict, diff, cost, 0, cfg)
    log.append(f"{sid}: verdict={verdict} -> {decision.value} | {reasons[0] if reasons else ''}")

    if decision == Decision.PROCEED_COMMIT:
        ok, msg = _safe_commit(repo, contract["allowed_paths"], contract["forbidden_paths"],
                               f"{sid}: {step.get('title','')}")
        if not ok:
            log.append(f"{sid}: commit yapılamadı ({msg}) -> rollback + imza.")
            _rollback(repo, checkpoint, tuple(contract["allowed_paths"]))
            step["status"] = "needs_human"
            step.setdefault("evidence", {}).update(
                {"verdict": verdict, "reason": msg, "at": datetime.now().strftime("%Y-%m-%d")})
            return "HUMAN_GATE"
        step["status"] = "done"
        step.setdefault("evidence", {}).update(
            {"commit": _head(repo), "verdict": verdict,
             "at": datetime.now().strftime("%Y-%m-%d")})
        return "PROCEED_COMMIT"

    if decision == Decision.HALT:
        _rollback(repo, checkpoint, tuple(contract["allowed_paths"]))
        return "HALT"

    # Buradan sonrası HUMAN_GATE veya FAIL kaynaklı REPAIR -> ikisi de imzaya gider.
    if verdict == "FAIL":
        # Bozuk değişiklikleri saklamanın anlamı yok: rollback. İnsan WHY'a bakar.
        _rollback(repo, checkpoint, tuple(contract["allowed_paths"]))
        step["status"] = "needs_human"
        step.setdefault("evidence", {}).update(
            {"verdict": "FAIL",
             "reason": f"runner repair tükendi (FAIL); bak: {reports_dir.name}/ + runner log",
             "reasons": reasons, "at": datetime.now().strftime("%Y-%m-%d")})
        log.append(f"{sid}: FAIL -> değişiklik geri alındı, sebep imzana bırakıldı.")
        return "HUMAN_GATE"
    # PASS ama yargı/hassasiyet kapısı -> geçerli değişikliği review dalına park et.
    branch = _park_to_review(repo, checkpoint, sid, contract["allowed_paths"],
                             f"review parking: {sid}")
    if not branch:
        # Review park commit başarısız -> rollback + HALT
        _rollback(repo, checkpoint, tuple(contract["allowed_paths"]))
        step["status"] = "needs_human"
        step.setdefault("evidence", {}).update(
            {"verdict": verdict, "reason": "review park commit failed",
             "at": datetime.now().strftime("%Y-%m-%d")})
        log.append(f"{sid}: PASS ama review park commit'i başarısız -> rollback + HAL.")
        return "HALT"
    step["status"] = "needs_human"
    step.setdefault("evidence", {}).update(
        {"review_branch": branch, "verdict": verdict, "reasons": reasons,
         "at": datetime.now().strftime("%Y-%m-%d")})
    log.append(f"{sid}: PASS ama imza gerekti -> {branch} dalına park, imzanı bekliyor.")
    return "HUMAN_GATE"


class StepPlan:
    def __init__(self, sid, contract, task_md):
        self.sid, self.contract, self.task_md = sid, contract, task_md


# --------------------------------------------------------------------------- #
# ana döngü
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JARVIS otonom inşa orchestrator (scaffold)")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--state", default="roadmap_state.json")
    ap.add_argument("--reports-dir", default=".verifier/reports")
    ap.add_argument("--runner", default="scripts/jarvis_auto_task.ps1")
    ap.add_argument("--contract-path", default="outcome_contract.active.json",
                    help="Üretilen contract buraya yazılır; runner buradan okumalı.")
    ap.add_argument("--task-dir", default=".verifier/tasks")
    ap.add_argument("--cost-ledger", default=None)
    ap.add_argument("--max-steps", type=int, default=5, help="Bu koşumda en fazla kaç adım.")
    ap.add_argument("--budget", type=float, default=None, help="Günlük USD bütçe (armed için zorunlu).")
    ap.add_argument("--arm", action="store_true", help="GERÇEKTEN çalıştır (yoksa dry-run).")
    ap.add_argument("--dry-run", action="store_true", help="Sadece planı yaz, hiçbir şey değiştirme.")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    state_path = repo / args.state if not Path(args.state).is_absolute() else Path(args.state)
    reports_dir = repo / args.reports_dir if not Path(args.reports_dir).is_absolute() else Path(args.reports_dir)
    runner = repo / args.runner if not Path(args.runner).is_absolute() else Path(args.runner)
    contract_path = repo / args.contract_path if not Path(args.contract_path).is_absolute() else Path(args.contract_path)
    task_dir = repo / args.task_dir if not Path(args.task_dir).is_absolute() else Path(args.task_dir)
    ledger = Path(args.cost_ledger) if args.cost_ledger else None

    armed = args.arm and not args.dry_run
    if args.arm and args.budget is None:
        print("RED: --arm için --budget zorunlu. (Otonomi açmadan önce bütçeyi belirle.)")
        return 2
    if armed and ledger is None:
        print("UYARI: cost ledger yok -> bütçe denetimi PASİF (maliyet hep $0 görünür).")
        if args.max_steps > 3:
            print("RED: ledger olmadan --max-steps>3 ile uzun otonom koşum açılamaz. "
                  "Runner'a cost_ledger.json yazımını ekle ya da --max-steps<=3 kullan.")
            return 2

    state = _load_state(state_path)
    pol = state.get("policy_defaults", {})
    cfg = PolicyConfig(
        budget_usd=float(args.budget) if args.budget is not None else float(pol.get("budget_usd", 5.0)),
        max_repair_rounds=int(pol.get("max_repair_rounds", 4)),
    )

    log: list[str] = []
    log.append(f"=== Orchestrator {'ARMED' if armed else 'DRY-RUN'} | "
               f"max_steps={args.max_steps} | budget=${cfg.budget_usd} ===")
    if armed and not runner.exists():
        print(f"RED: runner bulunamadı: {runner}")
        return 2

    steps_done = 0
    while steps_done < args.max_steps:
        if _cost_so_far(ledger) >= cfg.budget_usd:
            log.append("Bütçe aşıldı -> HALT."); break
        # İmza/karar kapısı bekleyen adım varsa, dur ve bildir.
        # Tetikleyen durumlar:
        #   a) status == needs_human (herhangi bir adım)
        #   b) status == in_progress AND yargı adımı (judgment/human)
        pending_steps = [s for s in state.get("steps", [])
                         if s.get("status") == "needs_human"
                         or (s.get("status") == "in_progress" and _is_judgment(s))]
        if pending_steps:
            log.append("Bekleyen imza/karar kapısı (çözülmeden yeni iş seçilmiyor): "
                       + ", ".join(s["id"] for s in pending_steps))
            break
        step = _select_next(state.get("steps", []))
        if step is None:
            log.append("Uygun adım kalmadı (hepsi bitti/bloke/imza bekliyor)."); break
        outcome = run_cycle(step, repo, state_path, state, reports_dir, runner,
                            contract_path, task_dir, cfg, ledger, armed, log)
        if armed:
            _save_state(state_path, state)
        steps_done += 1
        if outcome in ("HALT",):
            break
        if outcome in ("HUMAN_GATE", "REPAIR", "DRY_RUN") and not armed:
            # dry-run: tek adımdan fazlasını planlamak için bir sonrakine geçemeyiz
            # (state değişmediği için _select_next aynı adımı döndürür) -> dur.
            break

    print("\n".join(log))
    # armed sonunda günlük rapor
    if armed:
        dr = Path(__file__).resolve().parent / "daily_report.py"
        if dr.exists():
            subprocess.run([sys.executable, str(dr), "--repo", str(repo),
                            "--state", str(state_path), "--reports-dir", str(reports_dir)]
                           + (["--cost-ledger", str(ledger)] if ledger else []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
