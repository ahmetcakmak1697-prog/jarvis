# CODEX_REVIEW_REQUEST.md — Review Request for Codex

---

## Task
T1-S1 — Turkish character quality test skeleton

## Commit
pending (to be filled after commit)

## Branch
auto/opencode-deepseek

## Files Changed
```
tests/test_tr_quality.py  (NEW — 13 tests)
```

## Tests Run
```
pytest tests/test_tr_quality.py -q --tb=short  →  13/13 PASS
```

## What to Review

1. **Correctness of Turkish fold expectations**:
   Are the expected fold outputs in `_TR_CASES` correct for all 7 chars?
   Specifically: is İ→i, ı→i, ğ→g, ş→s, ç→c, ö→o, ü→u the right ASCII-fold mapping?

2. **Python combining-dot test**:
   `test_python_dotted_capital_i_lower_produces_combining_dot` asserts `"İ".lower()` gives
   `'i' + U+0307`. Is this accurate for CPython 3.11?

3. **Coverage gaps**:
   Are there Turkish encoding edge cases not covered here that should be regression-guarded?
   (e.g. Turkish capital dotless I → Ş, Ğ, Ü, Ö uppercase variants)

4. **Both modules**: We test `_fold_tr` from both `agents.data_classifier` and
   `agents.assistant_executor`. Is it intentional to have two copies? Should the
   consistency test be a canary that they stay in sync?

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---
*Prepared by: Claude Code | Date: 2026-06-24*
