"""
Wake Word Detection - "Jarvis" dediğinde aktive olur
openWakeWord kütüphanesi gerekli: pip install openwakeword
RTX 3070'de CPU'da bile çalışır, hafif.

KULLANIM:
  from tools.wake_word import WakeWordDetector
  wd = WakeWordDetector()
  wd.listen_until_wake()  # "Jarvis" diyene kadar bekler
  # Bundan sonra normal voice_io.listen() çalışır
"""
import time

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False


class WakeWordDetector:
    def __init__(self, model_name: str = "alexa", threshold: float = 0.5):
        """
        model_name: openwakeword'deki built-in modeller
          'alexa', 'hey_jarvis', 'hey_mycroft', 'hey_rhasspy'
        threshold: 0.0-1.0, ne kadar emin olunca tetiklesin
        """
        self.threshold = threshold
        self.model_name = model_name
        self._oww = None

    def _init_oww(self):
        if self._oww is not None:
            return True
        try:
            from openwakeword.model import Model
            self._oww = Model(wakeword_models=[self.model_name],
                              inference_framework='onnx')
            return True
        except ImportError:
            print("⚠️ openwakeword yok: pip install openwakeword")
            return False
        except Exception as e:
            print(f"⚠️ WakeWord init hatası: {e}")
            return False

    def listen_until_wake(self, timeout: int = 0) -> bool:
        """
        timeout=0 → süresiz dinle
        timeout=N → N saniye dinle, bulamazsa False döner
        """
        if not AUDIO_OK:
            print("⚠️ sounddevice yok: pip install sounddevice scipy")
            return False
        if not self._init_oww():
            return False

        sample_rate = 16000
        chunk_size = 1280  # 80ms
        start = time.time()

        print(f"🎤 'Jarvis' bekleniyor...")

        try:
            with sd.InputStream(samplerate=sample_rate, channels=1,
                                dtype='int16', blocksize=chunk_size) as stream:
                while True:
                    if timeout and (time.time() - start) > timeout:
                        return False

                    audio_chunk, _ = stream.read(chunk_size)
                    audio_np = np.frombuffer(audio_chunk, dtype=np.int16)

                    predictions = self._oww.predict(audio_np)
                    for word, score in predictions.items():
                        if score >= self.threshold:
                            print(f"✅ Wake: {word} ({score:.2f})")
                            return True
        except Exception as e:
            print(f"⚠️ Dinleme hatası: {e}")
            return False

    def is_available(self) -> bool:
        return AUDIO_OK and self._init_oww()


if __name__ == "__main__":
    wd = WakeWordDetector()
    if wd.is_available():
        print("Hazır. 'Jarvis' deyin...")
        wd.listen_until_wake()
        print("🎯 Aktive oldu!")
    else:
        print("Kullanılamıyor")
