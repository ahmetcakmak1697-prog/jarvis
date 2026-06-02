import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd, name, allow_fail=False):
    print(f"\n=== {name} ===")
    print(" ".join(cmd))

    p = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False
    )

    if p.stdout.strip():
        print(p.stdout.strip())

    if p.stderr.strip():
        print(p.stderr.strip())

    if p.returncode != 0 and not allow_fail:
        raise SystemExit(f"FAIL: {name}")

    return p

def main():
    print("JARVIS A5 SMOKE SUITE")

    run(
        [sys.executable, "-m", "py_compile", "jarvis_server.py", "jarvis_brain.py"],
        "Python compile"
    )

    run(
        [sys.executable, "tests/brain_chat_return_smoke.py"],
        "Brain chat return smoke"
    )

    run(
        [sys.executable, "tests/ws_auth_unauthorized_smoke.py"],
        "WebSocket unauthorized smoke",
        allow_fail=False
    )

    run(
        [sys.executable, "tests/proactive_core_smoke.py"],
        "Proactive core smoke"
    )

    run(
        [sys.executable, "tests/c1_memory_smoke_suite.py"],
        "C1 memory smoke suite"
    )

    tracked_sensitive = run(
        ["git", "ls-files"],
        "Git tracked files scan"
    ).stdout.splitlines()

    bad_terms = [
        ".env",
        "venv/",
        "__pycache__",
        "logs/",
        ".zip",
        "chroma_db",
        "sqlite",
        "jarvis_memory.db",
        "train_data",
    ]

    allowed = {".env.example"}

    bad = []
    for file in tracked_sensitive:
        if file in allowed:
            continue
        low = file.lower()
        if any(term.lower() in low for term in bad_terms):
            bad.append(file)

    if bad:
        print("\nTracked sensitive/runtime files found:")
        for item in bad:
            print(" -", item)
        raise SystemExit("FAIL: Git sensitive/runtime scan")

    print("\nA5 smoke OK")
    print("Efendim, temel sistem bütünlüğü doğrulandı.")

if __name__ == "__main__":
    main()
