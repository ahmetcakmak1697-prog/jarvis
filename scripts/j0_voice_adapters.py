"""
scripts/j0_voice_adapters.py — STT adapter layer for J0 voice pipeline.

Default-off. RealtimeSTTAdapter does NOT import RealtimeSTT at module level.
Import safety is tested: importing this module must not import RealtimeSTT,
sounddevice, or pyaudio, and must not touch any audio device.

Windows multiprocessing requirement: any process entrypoint that constructs
a RealtimeSTTAdapter and calls start() or listen() MUST be guarded by
    if __name__ == "__main__":
because RealtimeSTT spawns child processes internally. Omitting this guard
causes child processes to re-execute module-level code, resulting in infinite
fork bombs on Windows.
"""
from __future__ import annotations

import importlib.util
from typing import Iterator, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class STTAdapter(Protocol):
    """Speech-to-text adapter interface."""

    def start(self) -> None:
        """Begin a listening session. May lazy-import real libs here."""
        ...

    def stop(self) -> None:
        """End the current listening session and release resources."""
        ...

    def listen(self) -> str:
        """Block until one utterance is recognized. Return text."""
        ...

    def is_available(self) -> bool:
        """Return True if the underlying library is locatable without importing it."""
        ...


# ---------------------------------------------------------------------------
# RealtimeSTTAdapter
# ---------------------------------------------------------------------------


class RealtimeSTTAdapter:
    """Wraps RealtimeSTT (MIT) behind STTAdapter.

    Constructor stores config ONLY.  No import of RealtimeSTT happens here.
    Lazy import occurs inside start() / listen() to preserve import safety.

    Default config targets Turkish with "hey jarvis" wake word and Silero VAD:
        model="small"           — faster-whisper model size
        language="tr"           — Turkish
        silero_sensitivity=0.4  — Silero VAD threshold
        wake_words="hey jarvis" — openWakeWord phrase
        wake_word_backend="oww" — openWakeWord backend

    Windows multiprocessing: caller MUST be inside `if __name__ == "__main__"`.
    """

    _DEFAULT_CONFIG: dict = {
        "model": "small",
        "language": "tr",
        "silero_sensitivity": 0.4,
        "wake_words": "hey jarvis",
        "wake_word_backend": "oww",
    }

    def __init__(self, **config_overrides) -> None:
        self._config: dict = {**self._DEFAULT_CONFIG, **config_overrides}
        self._recorder = None  # populated by start()

    @property
    def config(self) -> dict:
        return dict(self._config)

    def is_available(self) -> bool:
        """Check RealtimeSTT importability without actually importing it."""
        try:
            spec = importlib.util.find_spec("RealtimeSTT")
            return spec is not None
        except Exception:
            return False

    def start(self) -> None:
        """Lazy-import RealtimeSTT and start the AudioToTextRecorder."""
        from RealtimeSTT import AudioToTextRecorder  # type: ignore[import]
        self._recorder = AudioToTextRecorder(**self._config)

    def listen(self) -> str:
        """Block until one utterance is recognized. Requires start() first."""
        if self._recorder is None:
            raise RuntimeError("RealtimeSTTAdapter.start() must be called before listen()")
        from RealtimeSTT import AudioToTextRecorder  # type: ignore[import]
        return self._recorder.text()

    def stop(self) -> None:
        """Stop the recorder and release audio resources."""
        if self._recorder is not None:
            try:
                self._recorder.stop()
            finally:
                self._recorder = None


# ---------------------------------------------------------------------------
# FakeSTTAdapter (tests only)
# ---------------------------------------------------------------------------


class FakeSTTAdapter:
    """Deterministic STT adapter for tests. Yields pre-injected texts in order.

    listen() raises IndexError when the injected list is exhausted — tests
    must control exactly how many listen() calls occur.
    """

    def __init__(self, texts: List[str]) -> None:
        self._texts: List[str] = list(texts)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def listen(self) -> str:
        if not self._texts:
            raise IndexError("FakeSTTAdapter: no more injected texts")
        return self._texts.pop(0)

    def is_available(self) -> bool:
        return True
