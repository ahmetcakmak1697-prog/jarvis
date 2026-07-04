"""
scripts/j0_voice_loop.py — Default-off voice loop skeleton (J0A).

Default-off: env JARVIS_J0_REALTIME_ENABLED (default "0").

CLI behaviour:
  env=0, any args:  print JSON {"status": "disabled", ...}; exit 0.
  env=1, no --real-mic:  print JSON {"status": "disabled", "reason": "--real-mic required"}; exit 0.
  env=1 + --real-mic:  real microphone path (only inside __main__; never called by tests).

All CLI output goes through scripts/_utf8io (configure_utf8_stdio + dump_json_to_stdout).

Turkish string literals in this file use \\uXXXX escapes (project rule: byte-safe on all platforms).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, List, Optional

# ---------------------------------------------------------------------------
# Route table (status intent detection)
# ---------------------------------------------------------------------------

_ROUTE_PHRASES: List[str] = [
    "nerede kaldık",           # nerede kaldik (i=U+0131)
    "son commit neydi",             # pure ASCII
    "en son ne yaptık",        # en son ne yaptik (i=U+0131)
    "bugün ne yapacağız",  # bugün ne yapacağız
]

# ASCII-fold table: Turkish special chars -> Latin base.
# Dict form: no length-counting required; keys use Unicode escapes per project rule.
_FOLD_TABLE = str.maketrans({
    "ç": "c",  # c-cedilla
    "ğ": "g",  # g-breve
    "ı": "i",  # dotless-i
    "ş": "s",  # s-cedilla
    "ö": "o",  # o-umlaut
    "ü": "u",  # u-umlaut
    "Ç": "c",  # C-cedilla
    "Ğ": "g",  # G-breve
    "İ": "i",  # Dotted-I — also pre-replaced before .lower()
    "Ş": "s",  # S-cedilla
    "Ö": "o",  # O-umlaut
    "Ü": "u",  # U-umlaut
})


def _ascii_fold(s: str) -> str:
    """Fold Turkish letters to ASCII equivalents for robust keyword matching.

    Handles the dot-I problem: İ (dotted-I) is replaced before .lower()
    because str.lower() converts it to 'i̇' (i + combining dot above),
    which the translate table cannot match. Explicit replace avoids the
    combining character. Both the query and route phrase are folded before
    comparison.
    """
    s = s.replace("İ", "i")  # dotted-I -> i before lower()
    return s.lower().translate(_FOLD_TABLE)


def _matches_status_intent(text: str) -> bool:
    """Return True if text matches any status-intent route phrase (fold-safe)."""
    folded_text = _ascii_fold(text)
    return any(_ascii_fold(phrase) in folded_text for phrase in _ROUTE_PHRASES)


# ---------------------------------------------------------------------------
# Core routing function
# ---------------------------------------------------------------------------

StatusProvider = Callable[[], object]
"""Callable that returns an object with a .text_summary() -> str method.

Used to inject a real or fake live-status provider. The real provider wraps
collect_status() from j0_live_status. Tests inject a fake.
"""


def route_and_respond(text: str, status_provider: Optional[StatusProvider] = None) -> str:
    """Route recognized text to the appropriate handler and return response.

    If text matches a status intent and status_provider is None, falls back to
    the live j0_live_status.collect_status(). Always prefer passing an explicit
    status_provider in tests to avoid real git subprocess calls.
    """
    if _matches_status_intent(text):
        if status_provider is not None:
            status = status_provider()
        else:
            _scripts = Path(__file__).parent
            if str(_scripts) not in sys.path:
                sys.path.insert(0, str(_scripts))
            from j0_live_status import (  # type: ignore[import]
                collect_status,
                _default_git_runner,
                _default_roadmap_loader,
            )
            status = collect_status(_default_git_runner, _default_roadmap_loader)
        return status.text_summary()

    return "Bu komutu anlayamadım."  # fallback: Bu komutu anlayamadim


# ---------------------------------------------------------------------------
# One-turn runner (injectable -- testable without hardware)
# ---------------------------------------------------------------------------


def run_one_turn(stt, tts, status_provider: Optional[StatusProvider] = None) -> str:
    """Execute one listen->route->speak cycle.

    stt: STTAdapter -- provides listen() -> str
    tts: TTSAdapter -- provides speak(text) -> TTSResult
    status_provider: optional callable returning status object with text_summary()

    Returns the response text that was passed to tts.speak().
    Never calls real microphone. Never called by tests through main().
    """
    text = stt.listen()
    response = route_and_respond(text, status_provider=status_provider)
    tts.speak(response)
    return response


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    _scripts = Path(__file__).parent
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))
    from _utf8io import configure_utf8_stdio, dump_json_to_stdout  # type: ignore[import]

    configure_utf8_stdio()

    enabled = os.environ.get("JARVIS_J0_REALTIME_ENABLED", "0") == "1"

    if not enabled:
        dump_json_to_stdout({
            "status": "disabled",
            "env": "JARVIS_J0_REALTIME_ENABLED=0",
            "config_summary": {
                "model": "small",
                "language": "tr",
                "wake_words": "hey jarvis",
                "wake_word_backend": "oww",
                "silero_sensitivity": 0.4,
            },
            "note": (
                "Set JARVIS_J0_REALTIME_ENABLED=1 and pass --real-mic "
                "to enable microphone input."
            ),
        })
        sys.exit(0)

    if "--real-mic" not in sys.argv:
        dump_json_to_stdout({
            "status": "disabled",
            "env": "JARVIS_J0_REALTIME_ENABLED=1",
            "reason": "--real-mic flag required for microphone access",
            "note": "Pass --real-mic explicitly to open the audio device.",
        })
        sys.exit(0)

    # Real microphone path -- only reachable when env=1 AND --real-mic.
    # Guarded by __main__ below. Never called by tests.
    from j0_voice_adapters import RealtimeSTTAdapter  # type: ignore[import]
    from j0_tts_adapters import FakeTTSAdapter  # type: ignore[import]

    print(
        "J0 voice loop starting. First run is warmup -- do not record timing.\n"
        "Say 'Hey Jarvis' then: nerede kaldik / son commit neydi / "
        "en son ne yaptik / bugun ne yapacagiz",
        file=sys.stderr,
    )

    stt = RealtimeSTTAdapter()
    tts = FakeTTSAdapter()  # Real TTS adapter wired in J0B

    stt.start()
    try:
        while True:
            response = run_one_turn(stt, tts)
            print(response)
    except KeyboardInterrupt:
        pass
    finally:
        stt.stop()


if __name__ == "__main__":
    main()
