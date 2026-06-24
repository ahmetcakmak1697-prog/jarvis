# CODEX_REVIEW_REQUEST.md — Review Request

---

## Status
PENDING_CODEX_REVIEW

## Branch
auto/opencode-deepseek

## Commits to Review

```
9bbdab0c4  fix(local-agent): inject compact current project state
926616582  fix(local-agent): ground project-status answers in automation docs
0b127e7cc  fix(cli): prevent rich markup crash in local mode diagnostic
```

Plus the T1-S2 sign-off recording commit (see git log -1).

## Files Changed

```
agent/local_agent.py
  - SYSTEM_PROMPT: added PROJE DURUMU KURALI grounding section
  - SYSTEM_PROMPT: fixed Turkish grammar (erisimim yok, zamanlayici)
  - _load_project_context(): replaces raw file snippet with structured
    GUNCEL PROJE DURUMU block: git log -5 --oneline (subprocess, read-only),
    HUMAN_NEEDED.md pending items, hardcoded known-state facts
  - chat(): injects _project_ctx before memory context

main.py
  - _run_local_mode(): balanced Rich markup tags in Ollama diagnostic
    (was: stray [/] caused crash; now: [yellow]...[/yellow] per line)

tests/test_local_agent_grounding.py  NEW — 8 grounding regression tests
tests/test_main_cli_markup.py        NEW — 2 Rich markup regression tests

roadmap_state.json          FAZ-T1.status: "todo" → "done" + evidence block
automation/T1_S2_SMOKE_RESULTS.md   NEW — Ahmet's sign-off evidence
automation/HUMAN_NEEDED.md  T1-S2 resolved; E1-S4/E1-S5 remain
automation/SESSION_SUMMARY.md       updated
automation/AUTONOMY_LOG.md          updated
```

## Tests Run

```
py -3.11 -m pytest tests/test_local_agent_grounding.py
                   tests/test_main_cli_markup.py
                   tests/test_tr_quality.py -q --tb=short
→ 23/23 PASS

git diff --check → clean
py -3.11 -m py_compile agent/local_agent.py main.py → OK
```

## Specific Review Questions for Codex

1. **subprocess in system prompt builder**: `_load_project_context()` calls
   `subprocess.run(["git", "log", "-5", "--oneline"], ...)` at agent startup.
   Is this safe enough for the local-only agent context?
   Risk: git not on PATH, cwd wrong, timeout too short (5s).
   Mitigation: full try/except, graceful fallback to empty string.

2. **Known-state hardcoding**: T1-S2/E1-S4/E1-S5 facts are hardcoded strings
   in `_load_project_context()`. When these gates are resolved, the hardcoded
   strings will become stale. Is this acceptable for now, or should they be
   read from roadmap_state.json directly?

3. **Rich markup fix**: The fix uses `[yellow]...[/yellow]` per line.
   The emoji `❌` is preserved on the red error line. Is this correct?
   (emoji was already there before; it was the stray `[/]` that crashed.)

4. **T1-S2 sign-off scope**: FAZ-T1 is marked "done" based on Ahmet's
   actual CLI smoke run (llama3.1, Ollama local). The sign-off covers
   Turkish character rendering and context grounding, with known limitation
   that local llama3.1 produces imperfect style. Is "PASS with minor wording
   concerns" an acceptable FAZ-T1 completion criterion?

## Forbidden Actions for Codex

- Do not edit .env
- Do not trigger live Telegram send
- Do not start scheduler or background loop
- Do not mark E1-S4 or E1-S5 as done
- Do not push

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-24*
