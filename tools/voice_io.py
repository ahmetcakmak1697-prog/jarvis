"""Voice I/O - Whisper local STT + Edge-TTS."""
import asyncio
from pathlib import Path
import tempfile


class VoiceIO:
    def __init__(self, whisper_model="small", tts_voice="tr-TR-AhmetNeural"):
        self.whisper_model_name = whisper_model
        self.tts_voice = tts_voice
        self._whisper = None

    def _ensure_whisper(self):
        if self._whisper is None:
            try:
                from faster_whisper import WhisperModel
                self._whisper = WhisperModel(
                    self.whisper_model_name, device="cuda",
                    compute_type="float16")
            except Exception:
                from faster_whisper import WhisperModel
                self._whisper = WhisperModel(
                    self.whisper_model_name, device="cpu", compute_type="int8")
        return self._whisper

    def transcribe(self, audio_path, language="tr"):
        m = self._ensure_whisper()
        segments, info = m.transcribe(str(audio_path), language=language,
                                      beam_size=5, vad_filter=True)
        text = " ".join(s.text for s in segments).strip()
        return {"text": text, "language": info.language,
                "duration": info.duration}

    def transcribe_bytes(self, audio_bytes, ext=".wav", language="tr"):
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            path = tmp.name
        try:
            return self.transcribe(path, language=language)
        finally:
            Path(path).unlink(missing_ok=True)

    async def speak_to_file(self, text, output_path):
        import edge_tts
        c = edge_tts.Communicate(text, self.tts_voice)
        await c.save(str(output_path))
        return str(output_path)

    def speak(self, text, output_path=None):
        if output_path is None:
            output_path = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False).name
        asyncio.run(self.speak_to_file(text, output_path))
        return output_path

    def record(self, duration=5, sample_rate=16000):
        import sounddevice as sd
        from scipy.io.wavfile import write
        rec = sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                     channels=1, dtype='int16')
        sd.wait()
        path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        write(path, sample_rate, rec)
        return path

    def listen(self, duration=5):
        path = self.record(duration)
        try:
            return self.transcribe(path)
        finally:
            Path(path).unlink(missing_ok=True)
