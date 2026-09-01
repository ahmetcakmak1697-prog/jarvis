"""
JARVIS Sesli Sistem — Edge TTS (Iron Man modu)
"""
import asyncio
import edge_tts
import pygame
import threading
import tempfile
from pathlib import Path


class JarvisVoice:
    # Türkçe sesler
    VOICE_TR_MALE = "tr-TR-AhmetNeural"      # Erkek, doğal
    VOICE_TR_FEMALE = "tr-TR-EmelNeural"     # Kadın
    
    # İngilizce JARVIS sesleri (Iron Man tarzı)
    VOICE_EN_JARVIS = "en-GB-RyanNeural"     # İngiliz aksanı, JARVIS gibi
    VOICE_EN_GUY = "en-US-GuyNeural"         # Amerikan, derin ses
    
    def __init__(self, voice: str = None, language: str = "tr"):
        self.language = language
        self.voice = voice or (self.VOICE_TR_MALE if language == "tr" else self.VOICE_EN_JARVIS)
        self.recognizer = None
        self.whisper = None
        
        pygame.mixer.init()
    
    def speak(self, text: str, async_mode: bool = False):
        text = text[:1000]
        if async_mode:
            threading.Thread(target=self._speak_blocking, args=(text,)).start()
        else:
            self._speak_blocking(text)
    
    def _speak_blocking(self, text: str):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            
            asyncio.run(self._generate_audio(text, tmp_path))
            
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            
            pygame.mixer.music.unload()
            Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            print(f"TTS hatasi: {e}")
    
    async def _generate_audio(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate="+0%",
            volume="+0%"
        )
        await communicate.save(output_path)
    
    def set_voice(self, voice_name: str):
        """Sesi değiştir: 'tr-male', 'tr-female', 'jarvis', 'guy'"""
        mapping = {
            "tr-male": self.VOICE_TR_MALE,
            "tr-female": self.VOICE_TR_FEMALE,
            "jarvis": self.VOICE_EN_JARVIS,
            "guy": self.VOICE_EN_GUY,
        }
        self.voice = mapping.get(voice_name, voice_name)
    
    def listen(self, timeout: int = 5) -> str:
        try:
            import speech_recognition as sr
            
            if self.recognizer is None:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 200
                self.recognizer.pause_threshold = 1.2
            
            with sr.Microphone() as source:
                print("[MIC] Dinliyorum...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout)
            
            print("[CPU] Cozumleniyor...")
            
            try:
                return self.recognizer.recognize_google(audio, language=f"{self.language}-TR")
            except Exception:
                return ""
        except Exception as e:
            return f"[Ses hatasi: {e}]"
    
    def _whisper_transcribe(self, audio) -> str:
        return ""