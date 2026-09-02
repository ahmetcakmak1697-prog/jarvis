# THIRD_PARTY_VOICE.md — Third-Party Voice Dependencies

> Date: 2026-07-04. Sprint: J0A.
> All versions and licenses marked [UNVERIFIED] until Ahmet grounds them.
> No legal conclusions are made in this sprint.

---

| Name | Version | License | Integration Method | Fallback if it breaks |
|---|---|---|---|---|
| RealtimeSTT | [UNVERIFIED] | MIT [UNVERIFIED] | dep-behind-adapter: lazy-imported inside RealtimeSTTAdapter.start()/listen(); never at module level | Fall back to j0_spike_b_latency_probe.py as diagnostic (legacy probe path) |
| faster-whisper | [UNVERIFIED] | MIT [UNVERIFIED] | via RealtimeSTT config (model="small", language="tr") | same as RealtimeSTT |
| openwakeword | [UNVERIFIED] | Apache-2.0 [UNVERIFIED] | via RealtimeSTT config (wake_word_backend="oww", wake_words="hey jarvis") | disable wake-word, use push-to-talk fallback |
| silero-vad | [UNVERIFIED] | MIT [UNVERIFIED] | via RealtimeSTT config (silero_sensitivity=0.4); torch model downloaded by RealtimeSTT | disable VAD, use fixed-window capture as diagnostic |
| sounddevice | [UNVERIFIED] | MIT [UNVERIFIED] | audio I/O for real microphone path; only active when JARVIS_J0_REALTIME_ENABLED=1 + --real-mic | no audio without it |
| Piper (tr_TR voice) | [UNVERIFIED] | GPL [UNVERIFIED] | Piper subprocess boundary preferred to reduce coupling and licensing/linking ambiguity; license must be verified before distribution/commercial use; no legal conclusion is made in this sprint. Stub in J0A (NotImplementedError); real subprocess = J0B | Edge TTS as default-off cloud fallback (J0B) |
| Edge TTS | [UNVERIFIED] | MIT [UNVERIFIED] | default-off cloud fallback; stub in J0A (NotImplementedError); no network calls in J0A | no TTS without it (degrade to text output) |

---

## Notes

- **Version grounding**: all versions above are TODO_VERIFY_VERSION until Ahmet runs `pip show <package>` after install and records the actual installed version here.
- **License grounding**: all licenses are [UNVERIFIED] until Ahmet or a licensed legal review confirms them from the package's own LICENSE file.
- **No install in J0A**: no package was installed during this sprint. Requirements are candidates only.
- **Piper binary**: Piper is not installed via pip. The binary is downloaded separately. See J0B for integration.
- **Model downloads**: Whisper "small" model (~244 MB) and openWakeWord "hey jarvis" model download on first run of j0_voice_loop.py --real-mic. Piper tr_TR voice model downloaded separately. These are not in the repo.
