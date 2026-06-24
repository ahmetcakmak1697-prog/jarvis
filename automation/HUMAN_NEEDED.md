# HUMAN_NEEDED.md — Items Requiring Ahmet

> Claude appends items here when work cannot proceed without Ahmet.
> Ahmet clears items after completing them.

---

## How to Use

- Claude adds an entry with date, task ID, and what exactly is needed.
- Ahmet acts and marks `[x] resolved: <date>`.
- Resolved items can be deleted after the next session.

**Note for Claude:** The comment-style template lines below (in `<!-- -->` blocks)
are placeholders. Do not treat them as real blockers. Only lines starting with
`- [ ]` outside comment blocks are real pending items.

---

## Pending Items

<!-- Add real items below this comment as they arise. Format:
- [ ] [YYYY-MM-DD] [TASK-ID] What is needed and exactly why Claude cannot proceed.
-->

*(none)*

---

## Resolved Items

<!-- Move resolved items here, then delete after next session. Format:
- [x] [YYYY-MM-DD] [TASK-ID] Description. Resolved: YYYY-MM-DD
-->

---

## Reference: What Always Requires Ahmet

Real examples of items that must be added here:

- Voice enrollment / wake-word recording / STT/TTS calibration
- Microphone / speaker hardware test
- Camera / room sensor / presence detection test
- Hardware pairing: Zigbee, Z-Wave, Sonoff, ESP32, Raspberry Pi
- Home Assistant live device control
- BMS / Niagara / Modbus / RS485 / industrial network access
- Router / firewall / network device config
- Camera system / NVR / DVR access
- Lock / alarm / security system
- API keys, tokens, secrets, `.env` edits
- Browser profile / session / cookie management
- SSH keys / certificate management
- Payment, purchase, subscription
- Email sending / official submission
- Destructive git: `reset --hard`, `clean -f`, `push --force`, `branch -D`
- Broad refactor spanning more than the current task scope
- Any live production system access
