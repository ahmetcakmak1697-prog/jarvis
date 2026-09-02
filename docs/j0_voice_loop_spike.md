# J0 Voice Loop Spike

## Spike-A: Repo skeleton (bu task)

- `scripts/j0_live_status.py` — live "nerede kald\u0131k" tool (git + roadmap, read-only, no RAG).
- `tests/test_j0_live_status.py` — 16 tests: Unicode, injectable, anti-staleness, conditional FAZ-3-E1.
- `scripts/j0_voice_latency_probe.py` — harness skeleton: dataclass, helper, Spike-A notice.
- `tests/test_j0_voice_latency_probe.py` — latency math, missing timestamps, TR-STT phrase spec.
- `docs/j0_voice_loop_spike.md` — this file.

Spike-A does NOT answer:
- Real wake->ilk-hece latency
- Real TR-STT accuracy
- RTX 3070 GPU sufficiency
- Real wake-word detection
- Real STT/TTS

Spike-A cannot install packages, use microphone, or call live web/API.

## Spike-B: Ahmet local PC (future)

- Microphone, model setup, STT/TTS packages allowed.
- Real wake->ilk-hece latency measurement.
- Real TR-STT accuracy with natural Turkish phrases.
- GPU decision after numbers.
- Real wake-word detection evaluation.

## Turkish Unicode output is a J0 blocker

User-facing labels are real Unicode Turkish:
- `\u00c7al\u0131\u015fma a\u011fac\u0131` (not `Calisma agaci`)
- `\u015eu an devam eden` (not `Su an devam eden`)
- `S\u0131ra bekleyen` (not `Sira bekleyen`)
- `TEM\u0130Z` / `K\u0130RL\u0130` (not `TEMIZ` / `KIRLI`)

No ASCII folding, no `.encode("ascii", ...)`, no mojibake.

## "Nerede kald\u0131k" is live tool state, not RAG

The tool reads `git log`, `git status`, and `roadmap_state.json`
at call time. No static text, no RAG snapshot, no hardcoded current focus.

## Governance

- Governance is frozen.
- FAZ-3-E1 is parked as in_progress (proactive policy engine done, delivery pending).
- No runtime delivery, Telegram send, scheduler, or background loop is claimed done.
- GPU decision only after Spike-B numbers.
