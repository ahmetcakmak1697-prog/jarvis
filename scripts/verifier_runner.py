"""
verifier_runner.py — deterministic developer automation gate.

Usage:
    py -3.11 scripts/verifier_runner.py <contract.json> [--diff-from <ref>]

Exit codes:
    0 = PASS
    1 = FAIL
    2 = NEEDS_HUMAN
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

# conservative secret-leak regexes — low false-positive
_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?i)(?:api[_-]?key|apikey|secret|token|password|passwd)["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}'),
    re.compile(r'(?i)(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36,}|gho_[A-Za-z0-9]{36,})'),
    re.compile(r'(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'),
    re.compile(r'(?i)-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----'),
]


def _load_contract(path: Path) -> dict[str, Any]:
    if not path.is_file():
        print(f"[VERIFIER] Contract not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[VERIFIER] Invalid contract: {exc}", file=sys.stderr)
        sys.exit(2)
    for key in ("task_id", "goal"):
        if key not in data:
            print(f"[VERIFIER] Missing required key: {key}", file=sys.stderr)
            sys.exit(2)
    return data


def _is_verifier_report(path_str: str) -> bool:
    return path_str.startswith(".verifier/") or "/.verifier/" in path_str


def _changed_files(diff_from: str | None) -> list[Path]:
    if not diff_from:
        diff_from = "HEAD"
    try:
        files: set[str] = set()
        # tracked changes (committed vs working tree)
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", diff_from],
            capture_output=True, text=True, check=False, cwd=ROOT,
        )
        if result.returncode == 0:
            for p in result.stdout.strip().splitlines():
                if p.strip() and not _is_verifier_report(p.strip()):
                    files.add(p.strip())
        # staged changes
        result2 = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "--cached"],
            capture_output=True, text=True, check=False, cwd=ROOT,
        )
        if result2.returncode == 0:
            for p in result2.stdout.strip().splitlines():
                if p.strip() and not _is_verifier_report(p.strip()):
                    files.add(p.strip())
        # unstaged tracked changes
        result3 = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, check=False, cwd=ROOT,
        )
        if result3.returncode == 0:
            for p in result3.stdout.strip().splitlines():
                if p.strip() and not _is_verifier_report(p.strip()):
                    files.add(p.strip())
        # untracked non-ignored files
        result4 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=False, cwd=ROOT,
        )
        if result4.returncode == 0:
            for p in result4.stdout.strip().splitlines():
                if p.strip() and not _is_verifier_report(p.strip()):
                    files.add(p.strip())
        return [ROOT / p for p in sorted(files)]
    except FileNotFoundError:
        print("[VERIFIER] git not available — cannot check changed files", file=sys.stderr)
        return []


def _path_is_allowed(path: Path, allowed: list[Path]) -> bool:
    for a in allowed:
        if path == a or a in path.parents:
            return True
    return False


def _path_is_forbidden(path: Path, forbidden: list[Path]) -> bool:
    for f in forbidden:
        if path == f or f in path.parents:
            return True
    return False


def _check_paths(
    changed: list[Path],
    allowed: list[str] | None,
    forbidden: list[str] | None,
) -> list[str]:
    errors: list[str] = []
    resolved_allowed = [(ROOT / a).resolve() for a in (allowed or [])]
    resolved_forbidden = [(ROOT / f).resolve() for f in (forbidden or [])]

    for cf in changed:
        cf_resolved = cf.resolve()
        if resolved_allowed and not _path_is_allowed(cf_resolved, resolved_allowed):
            errors.append(f"File outside allowed_paths: {cf}")
        if _path_is_forbidden(cf_resolved, resolved_forbidden):
            errors.append(f"File in forbidden_paths: {cf}")
    return errors


def _scan_for_secrets(paths: list[Path]) -> list[str]:
    leaks: list[str] = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for pat in _SECRET_PATTERNS:
                if pat.search(line):
                    rel = p.relative_to(ROOT) if p.is_relative_to(ROOT) else p
                    leaks.append(f"{rel}:{line_no} matches {pat.pattern[:40]}")
                    break
    return list(dict.fromkeys(leaks))


_PYTEST_COLLECT_FORMS = [
    re.compile(r'collected\s+(\d+)\s+(?:tests?|items?)\s+in', re.IGNORECASE),
    re.compile(r'(\d+)\s+(?:tests?|items?)\s+collected', re.IGNORECASE),
    re.compile(r'collected\s+(\d+)\s+(?:tests?|items?)', re.IGNORECASE),
]


def _parse_pytest_collected_count(output: str) -> int | None:
    for pat in _PYTEST_COLLECT_FORMS:
        m = pat.search(output)
        if m:
            return int(m.group(1))
    return None


def _fallback_count_nodeids(output: str) -> int | None:
    count = 0
    for line in output.splitlines():
        if "::" in line and line.strip():
            count += 1
    return count if count > 0 else None


def _check_pytest_collection(
    contract: dict[str, Any],
) -> tuple[int | None, int | None, str | None]:
    minimum = contract.get("minimum_pytest_collected", 0)
    if not minimum or minimum <= 0:
        return None, None, None
    try:
        result = subprocess.run(
            ["py", "-3.11", "-m", "pytest", ".\\tests\\", "--collect-only", "-q"],
            capture_output=True, text=True, check=False, cwd=ROOT,
        )
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode != 0:
            err = result.stderr.strip()[:500] or result.stdout.strip()[:500]
            return minimum, None, f"pytest collection command failed: {err}"
        actual = _parse_pytest_collected_count(combined)
        if actual is not None:
            return minimum, actual, None
        fallback = _fallback_count_nodeids(result.stdout)
        if fallback is not None:
            return minimum, fallback, f"fallback nodeid count used (summary parse failed); actual={fallback}"
        return minimum, None, "could not parse collected count from pytest output"
    except FileNotFoundError:
        return minimum, None, "py executable not found"


def _run_commands(commands: list[str]) -> list[str]:
    failures: list[str] = []
    for cmd in commands:
        print(f"[VERIFIER] Running: {cmd}")
        # shell=True is needed for pipes/args; we only run configured commands
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        if result.returncode != 0:
            out = result.stdout.strip()[:500]
            err = result.stderr.strip()[:500]
            failures.append(f"FAILED: {cmd}\n  stdout: {out}\n  stderr: {err}")
        else:
            print(f"[VERIFIER] OK: {cmd}")
    return failures


def _make_report(
    contract: dict[str, Any],
    path_errors: list[str],
    secret_leaks: list[str],
    command_failures: list[str],
    pytest_collection: tuple[int | None, int | None, str | None] = (None, None, None),
) -> dict[str, Any]:
    has_forbidden_paths = bool(path_errors)
    has_secrets = bool(secret_leaks)
    has_failures = bool(command_failures)
    human_required = contract.get("human_review_required", False)

    minimum_collected, actual_collected, collection_error = pytest_collection
    has_collection_failure = False
    if minimum_collected is not None and minimum_collected > 0:
        if collection_error:
            has_collection_failure = True
        elif actual_collected is not None and actual_collected < minimum_collected:
            has_collection_failure = True

    if has_forbidden_paths or has_secrets or has_failures or has_collection_failure:
        verdict = "FAIL"
        exit_code = 1
    elif human_required:
        verdict = "NEEDS_HUMAN"
        exit_code = 2
    else:
        verdict = "PASS"
        exit_code = 0

    report: dict[str, Any] = {
        "verifier_version": "1.0.0",
        "task_id": contract.get("task_id"),
        "goal": contract.get("goal"),
        "verdict": verdict,
        "exit_code": exit_code,
        "path_violations": path_errors,
        "secret_leaks": secret_leaks,
        "command_failures": command_failures,
        "human_review_required": human_required,
    }
    if minimum_collected is not None:
        report["minimum_pytest_collected"] = minimum_collected
        report["actual_pytest_collected"] = actual_collected
        report["pytest_collection_error"] = collection_error
    return report


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <contract.json> [--diff-from <ref>]", file=sys.stderr)
        return 2

    contract_path = Path(sys.argv[1]).resolve()
    diff_from: str | None = None
    if "--diff-from" in sys.argv:
        idx = sys.argv.index("--diff-from")
        if idx + 1 < len(sys.argv):
            diff_from = sys.argv[idx + 1]

    contract = _load_contract(contract_path)
    print(f"[VERIFIER] Contract: {contract.get('task_id')} — {contract.get('goal')}")

    changed = _changed_files(diff_from)
    path_errors = _check_paths(
        changed,
        contract.get("allowed_paths"),
        contract.get("forbidden_paths"),
    )
    if path_errors:
        print("[VERIFIER] PATH VIOLATIONS:")
        for e in path_errors:
            print(f"  ! {e}")

    secret_leaks = _scan_for_secrets(changed)
    if secret_leaks:
        print("[VERIFIER] SECRET LEAKS DETECTED:")
        for s in secret_leaks:
            print(f"  ! {s}")

    command_failures = _run_commands(contract.get("required_commands", []))
    if command_failures:
        print("[VERIFIER] COMMAND FAILURES:")
        for f in command_failures:
            print(f"  ! {f}")

    pytest_collection = _check_pytest_collection(contract)
    minimum_collected, actual_collected, collection_error = pytest_collection
    if minimum_collected is not None and minimum_collected > 0:
        print(f"[VERIFIER] Pytest collection minimum={minimum_collected} actual={actual_collected} error={collection_error}")
        if collection_error:
            print(f"  ! Collection error: {collection_error}")
        elif actual_collected is not None and actual_collected < minimum_collected:
            print(f"  ! Collected {actual_collected} items, expected at least {minimum_collected}")

    report = _make_report(contract, path_errors, secret_leaks, command_failures, pytest_collection)
    report_path = ROOT / ".verifier" / "reports" / f"verifier_report_{contract.get('task_id', 'unknown')}.json"
    _write_report(report, report_path)
    print(f"[VERIFIER] Report written: {report_path}")
    print(f"[VERIFIER] Verdict: {report['verdict']} (exit {report['exit_code']})")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
