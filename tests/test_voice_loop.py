"""voice/voice_loop.py sozlesmesi — sesli giris/cikis + klavye yedegi.

Temel kural: SES ASLA TEK YOL DEGILDIR. Mikrofon yoksa, Whisper coker,
sentez basarisiz olur ya da kullanici susarsa JARVIS kullanilamaz hale
GELMEZ; klavyeye duser. Ses bir kolaylik katmanidir, bir bagimlilik degil.
"""
from __future__ import annotations

import pytest


class FakeListener:
    def __init__(self, *results):
        self._results = list(results)
        self.calls = 0

    def listen(self):
        self.calls += 1
        if self._results:
            return self._results.pop(0)
        raise AssertionError("beklenenden fazla dinleme cagrisi")


class FakeSpeaker:
    def __init__(self, ok=True, patlat=False):
        self.spoken = []
        self._ok = ok
        self._patlat = patlat

    def speak(self, text):
        if self._patlat:
            raise RuntimeError("hoparlor yok")
        self.spoken.append(text)

        class _R:
            ok = self._ok
            warning = None
        return _R()


def stt(ok, text="", warning=None):
    from voice.stt import STTResult

    return STTResult(ok=ok, text=text, warning=warning)


# --------------------------------------------------------------------------- #
# 1. prompt(): ses -> metin, basarisizlikta klavye
# --------------------------------------------------------------------------- #

def test_prompt_returns_transcribed_speech():
    from voice.voice_loop import VoiceIO

    io = VoiceIO(
        listener=FakeListener(stt(True, "nerede kaldik")),
        speaker=FakeSpeaker(),
        keyboard=lambda p: pytest.fail("ses calisirken klavye sorulmamali"),
    )
    assert io.prompt() == "nerede kaldik"


def test_prompt_falls_back_to_keyboard_when_stt_fails():
    from voice.voice_loop import VoiceIO

    io = VoiceIO(
        listener=FakeListener(stt(False, warning="stt_no_input: no_speech_detected")),
        speaker=FakeSpeaker(),
        keyboard=lambda p: "klavyeden yazildi",
    )
    assert io.prompt() == "klavyeden yazildi"


def test_prompt_uses_keyboard_when_voice_disabled():
    from voice.voice_loop import VoiceIO

    io = VoiceIO(
        listener=FakeListener(),  # cagrilirsa patlar
        speaker=FakeSpeaker(),
        keyboard=lambda p: "sadece klavye",
        enabled=False,
    )
    assert io.prompt() == "sadece klavye"


def test_prompt_survives_listener_exception():
    """Dinleyici istisna firlatirsa bile klavyeye dusulur."""
    from voice.voice_loop import VoiceIO

    class Patlayan:
        def listen(self):
            raise RuntimeError("ses cihazi kayboldu")

    io = VoiceIO(
        listener=Patlayan(),
        speaker=FakeSpeaker(),
        keyboard=lambda p: "yedek",
    )
    assert io.prompt() == "yedek"


# --------------------------------------------------------------------------- #
# 2. say(): konusur, ama asla cokmez
# --------------------------------------------------------------------------- #

def test_say_speaks_when_enabled():
    from voice.voice_loop import VoiceIO

    sp = FakeSpeaker()
    VoiceIO(listener=FakeListener(), speaker=sp, keyboard=lambda p: "").say("merhaba")
    assert sp.spoken == ["merhaba"]


def test_say_is_silent_when_disabled():
    from voice.voice_loop import VoiceIO

    sp = FakeSpeaker()
    VoiceIO(listener=FakeListener(), speaker=sp, keyboard=lambda p: "",
            enabled=False).say("merhaba")
    assert sp.spoken == []


def test_say_never_raises():
    """Hoparlor patlarsa sohbet durmaz."""
    from voice.voice_loop import VoiceIO

    io = VoiceIO(listener=FakeListener(), speaker=FakeSpeaker(patlat=True),
                 keyboard=lambda p: "")
    io.say("bu patlamamali")  # istisna cikmamali


def test_say_skips_empty_text():
    from voice.voice_loop import VoiceIO

    sp = FakeSpeaker()
    io = VoiceIO(listener=FakeListener(), speaker=sp, keyboard=lambda p: "")
    io.say("")
    io.say("   ")
    assert sp.spoken == []


# --------------------------------------------------------------------------- #
# 3. Konusma metni hazirligi
# --------------------------------------------------------------------------- #

def test_markdown_is_stripped_before_speaking():
    """TTS yildiz, kare ve backtick OKUMAMALI."""
    from voice.voice_loop import speech_text

    kaynak = "## Baslik\n\n**kalin** ve `kod` ve *egik*\n\n- madde bir\n- madde iki"
    cikti = speech_text(kaynak)
    for isaret in ("#", "*", "`", "-"):
        assert isaret not in cikti, f"{isaret!r} seslendirilecek metinde kalmis"
    assert "Baslik" in cikti
    assert "kalin" in cikti
    assert "madde bir" in cikti


def test_code_blocks_are_replaced_not_read_aloud():
    from voice.voice_loop import speech_text

    kaynak = "Once sunu dene:\n\n```python\nfor i in range(10):\n    print(i)\n```\n\nSonra bak."
    cikti = speech_text(kaynak)
    assert "range" not in cikti
    assert "print" not in cikti
    assert "Once sunu dene" in cikti
    assert "Sonra bak" in cikti


def test_speech_text_is_length_capped():
    """Uzun cevabin tamami sesli okunmaz."""
    from voice.voice_loop import SPEECH_MAX_CHARS, speech_text

    uzun = "cumle. " * 500
    cikti = speech_text(uzun)
    assert len(cikti) <= SPEECH_MAX_CHARS + 40  # kirpma notu payi


def test_speech_text_handles_empty():
    from voice.voice_loop import speech_text

    assert speech_text("") == ""
    assert speech_text(None) == ""
