"""
jarvis/voice/voice_interface.py
─────────────────────────────────────────────────────────
ADIM 5 — Ses Arayüzü

STT: OpenAI Whisper (yerel, ücretsiz)
TTS: Microsoft Edge TTS (ücretsiz, yüksek kalite)

Kullanım:
    voice = VoiceInterface()
    text  = voice.listen()        # Mikrofon → metin
    voice.speak("Merhaba efendim") # Metin → ses
"""
from __future__ import annotations

import asyncio
import io
import tempfile
import threading
from pathlib import Path

from config import (
    VOICE_ENABLED, WHISPER_MODEL, TTS_VOICE,
    SAMPLE_RATE, SILENCE_THRESHOLD, SILENCE_DURATION, JARVIS_NAME
)
from rich.console import Console

console = Console()


class VoiceInterface:
    """
    VOICE_ENABLED=false ise tüm metodlar sessizce atlanır.
    """
    def __init__(self):
        self.enabled = VOICE_ENABLED
        self._whisper = None
        self._sd      = None

        if not self.enabled:
            console.print("[dim]Ses devre dışı (VOICE_ENABLED=false)[/]")
            return

        self._load_whisper()
        self._load_sounddevice()

    # ────────────────────────────────────────────────────
    def _load_whisper(self):
        try:
            import whisper
            console.print(f"[cyan]Whisper yükleniyor ({WHISPER_MODEL})...[/]")
            self._whisper = whisper.load_model(WHISPER_MODEL)
            console.print("[green]Whisper hazır ✓[/]")
        except ImportError:
            console.print("[red]openai-whisper kurulu değil → pip install openai-whisper[/]")
            self.enabled = False

    def _load_sounddevice(self):
        try:
            import sounddevice as sd
            import numpy as np
            self._sd  = sd
            self._np  = np
        except ImportError:
            console.print("[red]sounddevice kurulu değil → pip install sounddevice[/]")
            self.enabled = False

    # ────────────────────────────────────────────────────
    def listen(self, timeout: float = 10.0) -> str:
        """
        Mikrofonu dinler, sessizlik algılayınca durur.
        Metni döndürür.
        """
        if not self.enabled:
            return input("Sen: ")   # Fallback: klavye

        sd = self._sd
        np = self._np

        console.print("[bold cyan]🎤 Dinliyorum...[/] (konuşun, sessizlikte durur)")

        frames    = []
        silence   = 0.0
        chunk     = int(SAMPLE_RATE * 0.1)  # 100ms chunk

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=8) as stream:
            while silence < SILENCE_DURATION:
                data, _ = stream.read(chunk)
                frames.append(data.copy())
                rms = float(np.sqrt(np.mean(data ** 2)))
                if rms < SILENCE_THRESHOLD:
                    silence += 0.1
                else:
                    silence = 0.0
                if len(frames) * 0.1 > timeout:
                    break

        audio = np.concatenate(frames, axis=0).flatten()
        console.print("[dim]İşleniyor...[/]")

        # Geçici dosyaya yaz → Whisper'a ver
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            import soundfile as sf
            sf.write(f.name, audio, SAMPLE_RATE)
            result = self._whisper.transcribe(f.name, language="tr")

        text = result["text"].strip()
        console.print(f"[green]Algılandı:[/] {text}")
        return text

    # ────────────────────────────────────────────────────
    def speak(self, text: str):
        """
        Metni Edge TTS ile sese dönüştürür ve çalar.
        Engelleme yapmaz (arka planda çalışır).
        """
        if not self.enabled:
            return
        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()
        thread.join()   # Senkron çağrı için bekle (ajan döngüsünde kullanışlı)

    def _speak_sync(self, text: str):
        try:
            import edge_tts
            import sounddevice as sd
            import soundfile as sf

            async def _gen():
                communicate = edge_tts.Communicate(text, TTS_VOICE)
                buf = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.write(chunk["data"])
                buf.seek(0)
                return buf

            buf = asyncio.run(_gen())

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(buf.read())
                fname = f.name

            data, fs = sf.read(fname)
            sd.play(data, fs)
            sd.wait()
        except ImportError:
            console.print("[yellow]edge-tts veya sounddevice kurulu değil[/]")
        except Exception as e:
            console.print(f"[red]TTS hatası: {e}[/]")

    # ────────────────────────────────────────────────────
    @staticmethod
    def list_voices():
        """Kullanılabilir Türkçe sesleri listeler."""
        try:
            import asyncio
            import edge_tts

            async def _list():
                voices = await edge_tts.list_voices()
                tr = [v for v in voices if v["Locale"].startswith("tr")]
                for v in tr:
                    print(f"  {v['ShortName']:35} {v['Gender']}")

            asyncio.run(_list())
        except ImportError:
            print("edge-tts kurulu değil")
