# CLAUDE_PLAN.md — T1-S1

## Selected Task
T1-S1 — Create tests/test_tr_quality.py skeleton

## Safety Classification
SAFE_AUTONOMOUS

## Files Expected to Touch
- tests/test_tr_quality.py (new)
- automation/CLAUDE_PLAN.md (this file)
- automation/SESSION_SUMMARY.md
- automation/GPT_REVIEW_PACKET.md

## Files Expected NOT to Touch
- agents/data_classifier.py
- agents/assistant_executor.py
- roadmap_state.json
- .env / secrets

## Plan
1. Create tests/test_tr_quality.py
   - Import _fold_tr from both agents.data_classifier and agents.assistant_executor
   - Guard: "İ".lower() Python combining-dot regression test
   - Round-trips: all 7 Turkish chars (İ→i, ı→i, ğ→g, ş→s, ç→c, ö→o, ü→u)
   - Consistency: both implementations produce identical output
   - No codepoint loss: non-empty input → non-empty output
   - Mojibake guard: no U+FFFD replacement chars in known outputs
   - Mixed-case inputs (İSTANBUL, şEHİR, GÜNEŞ)
2. pytest tests/test_tr_quality.py -q --tb=short
3. If pass: commit, update docs

## Risks
- _fold_tr is private (prefixed _); importable from both modules (already confirmed by grep)
- Both implementations are identical; consistency test will trivially pass — intentional regression guard

---
*Written by: Claude Code | Date: 2026-06-24*
