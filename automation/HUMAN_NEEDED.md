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



- [ ] [2026-09-06] [CODEX-A-20260906] A denetimi BLOCKER/CONCERN bulgulari acik: [rapor](CODEX_A_DOGRULAMA_2026-09-06.md). V2-HANDOFF: Ahmet KART_CODEX_B08_B10_v2.md ile devam iznini ve B08 eski girisin emekliligini onayladi. A-01/A-02/A-04/A-06/A-07 Claude'da; Codex'in A-03/A-05 ve B08-B10 uygulamasi tamamlandi (CODEX_V2_SONUC_2026-09-08.md). Claude maddeleri bu kayitla yeniden onaylanmaz. Bu madde artik B uygulamasinin izin engeli degil; kalan A duzeltmelerinin takibidir.

<!-- Add real items below this comment as they arise. Format:
- [ ] [YYYY-MM-DD] [TASK-ID] What is needed and exactly why Claude cannot proceed.
-->


---

## Resolved Items

- [x] [2026-09-08] [CODEX-B10-GUARD-CONTRACT-20260908] Ahmet dort eski testi GUCLENDIRME onayi verdi. Sifir dis cagri + yerel yanit ve fail-closed iddialari eklendi. Iki tam sirada 1891 passed + 1 xfailed; Ruff 283; bagimsiz PASS. [Sonuc](CODEX_V2_SONUC_2026-09-08.md).

- [x] [2026-09-08] [CODEX-B09-PATHSPEC-20260907] Ahmet duzeltmeye ve B10'a devam iznini verdi. Her iki git_diff dali degisen dosya listesinde tam ad eslesmesi kullaniyor; dizin/eksik yol/index-dizin varyantlari once RED, sonra GREEN. Bagimsiz yeniden inceleme PASS; 67 odak testi gecti. Tarihsel durma kaydi: [CODEX_V2_UYGULAMA_2026-09-07.md](CODEX_V2_UYGULAMA_2026-09-07.md).

<!-- Move resolved items here, then delete after next session. Format:
- [x] [YYYY-MM-DD] [TASK-ID] Description. Resolved: YYYY-MM-DD
-->

- [x] [2026-06-24] [E1-S4] Live Telegram proactive smoke test. Resolved: 2026-06-27. Ahmet ran `py -3.11 -m agents.proactive_runner --e1-s4-smoke` and confirmed phone receipt; signed "Ahmet (phone receipt confirmed)". One message sent, no scheduler/retry/background loop; token and chat_id not exposed. Codex PASS on wiring commit a39db4568 (33/33 wiring + 157/157 regression). Evidence: `roadmap_state.json` -> FAZ-3-E1.evidence.e1_s4.
- [x] [2026-06-24] [T1-S2] Turkish quality subjective sign-off. Resolved: 2026-06-24. Ahmet ran python main.py (llama3.1 local), confirmed Turkish chars correct, no mojibake, project context grounded. PASS with minor wording concerns. See automation/T1_S2_SMOKE_RESULTS.md.
- [x] [2026-06-24] [E1-S5] Scheduler architecture decision. Resolved: 2026-06-24. Ahmet approved: Windows Task Scheduler + one-shot runner + default dry-run. See automation/SCHEDULER_DECISION.md.

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
