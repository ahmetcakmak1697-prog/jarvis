"""voice/voice_loop.py — sesli giriş/çıkış katmanı ve klavye yedeği.

Eşik 1'in son parçası: kulak (`voice/stt.py`) ile ağzı
(`scripts/j0_tts_adapters.py`) `main.py`'nin sohbet döngüsüne bağlar.

**Temel kural: ses asla tek yol değildir.** Mikrofon yoksa, Whisper çökerse,
sentez başarısız olursa ya da Ahmet sadece susarsa JARVIS kullanılamaz hâle
gelmez — klavyeye düşer. Ses bir kolaylık katmanıdır, bir bağımlılık değil.
Bu yüzden bu modüldeki hiçbir yol istisna sızdırmaz.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

__all__ = ["SPEECH_MAX_CHARS", "speech_text", "VoiceIO", "build_default_voice_io"]

#: Uzun bir cevabın tamamı sesli okunmaz; ekranda zaten tamamı var.
SPEECH_MAX_CHARS = 600

_KOD_BLOGU = re.compile(r"```.*?```", re.DOTALL)
_SATIRICI_KOD = re.compile(r"`([^`]*)`")
_BASLIK = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_MADDE = re.compile(r"^\s{0,3}[-*+]\s+", re.MULTILINE)
_VURGU = re.compile(r"(\*{1,3})(.+?)\1", re.DOTALL)
_BAGLANTI = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_COKLU_BOSLUK = re.compile(r"\n{3,}")


def speech_text(text: Optional[str]) -> str:
    """Markdown'ı seslendirilebilir düz metne çevirir.

    TTS yıldız, kare ve backtick okumamalı; kod blokları hiç okunmamalı —
    "for i in range on parantez" duymak istemiyoruz.
    """
    if not text or not str(text).strip():
        return ""

    t = str(text)
    t = _KOD_BLOGU.sub(" (kod bloğu ekranda) ", t)
    t = _BAGLANTI.sub(r"\1", t)
    t = _SATIRICI_KOD.sub(r"\1", t)
    t = _BASLIK.sub("", t)
    t = _MADDE.sub("", t)
    t = _VURGU.sub(r"\2", t)
    t = t.replace("`", "").replace("*", "").replace("#", "")
    t = _COKLU_BOSLUK.sub("\n\n", t).strip()

    if len(t) > SPEECH_MAX_CHARS:
        kesim = t.rfind(" ", 0, SPEECH_MAX_CHARS)
        if kesim < SPEECH_MAX_CHARS // 2:
            kesim = SPEECH_MAX_CHARS
        t = t[:kesim].rstrip() + ". Devamı ekranda efendim."
    return t


class VoiceIO:
    """Sesli giriş/çıkış; her başarısızlıkta sessizce klavyeye düşer.

    ``listener``  : ``listen() -> STTResult``
    ``speaker``   : ``speak(text) -> TTSResult``
    ``keyboard``  : ``(prompt: str) -> str``
    ``notify``    : kullanıcıya durum satırı basmak için (opsiyonel)
    """

    def __init__(
        self,
        listener=None,
        speaker=None,
        keyboard: Optional[Callable[[str], str]] = None,
        notify: Optional[Callable[[str], None]] = None,
        enabled: bool = True,
    ) -> None:
        self._listener = listener
        self._speaker = speaker
        self._keyboard = keyboard or (lambda p: input(p))
        self._notify = notify or (lambda m: None)
        self.enabled = enabled
        #: Ses tarafı üst üste başarısız olursa kendiliğinden kapanır ki
        #: her turda aynı hatayı tekrar denemeyelim.
        self._ardarda_hata = 0
        self._hata_siniri = 3

    def _duyur(self, mesaj: str) -> None:
        try:
            self._notify(mesaj)
        except Exception:  # noqa: BLE001 - bildirim asla akışı bozmaz
            pass

    def prompt(self, keyboard_prompt: str = "Sen: ") -> str:
        """Bir tur girdi al: önce mikrofon, olmazsa klavye."""
        if self.enabled and self._listener is not None:
            try:
                sonuc = self._listener.listen()
            except Exception as exc:  # noqa: BLE001
                sonuc = None
                self._duyur(f"[ses] dinleme hatası: {exc}")

            if sonuc is not None and getattr(sonuc, "ok", False):
                self._ardarda_hata = 0
                metin = (getattr(sonuc, "text", "") or "").strip()
                if metin:
                    self._duyur(f"[duydum] {metin}")
                    return metin
            else:
                if sonuc is not None:
                    self._duyur(f"[ses] {getattr(sonuc, 'warning', '') or 'girdi yok'}")
                self._ardarda_hata += 1
                if self._ardarda_hata >= self._hata_siniri:
                    self.enabled = False
                    self._duyur(
                        "[ses] üst üste başarısız — ses girişi kapatıldı, "
                        "klavye devam ediyor"
                    )

        try:
            return self._keyboard(keyboard_prompt)
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as exc:  # noqa: BLE001
            self._duyur(f"[girdi] okunamadı: {exc}")
            return ""

    def say(self, text: Optional[str]) -> None:
        """Cevabı seslendir. Başarısızlık sohbeti durdurmaz."""
        if not self.enabled or self._speaker is None:
            return
        konusulacak = speech_text(text)
        if not konusulacak:
            return
        try:
            sonuc = self._speaker.speak(konusulacak)
        except Exception as exc:  # noqa: BLE001
            self._duyur(f"[ses] seslendirme hatası: {exc}")
            return
        if sonuc is not None and not getattr(sonuc, "ok", True):
            self._duyur(f"[ses] {getattr(sonuc, 'warning', '') or 'seslendirilemedi'}")


def build_default_voice_io(
    keyboard: Optional[Callable[[str], str]] = None,
    notify: Optional[Callable[[str], None]] = None,
    enabled: bool = True,
    whisper_model: str = "small",
    tts_voice: str = "tr-TR-AhmetNeural",
) -> VoiceIO:
    """Gerçek donanımla bağlı bir VoiceIO kurar.

    Ağır bağımlılıklar (sounddevice, faster-whisper, edge-tts, pygame) burada,
    çağrı anında import edilir — bu modülü import etmek hiçbirini yüklemez.
    Kurulum başarısız olursa ses kapalı bir VoiceIO döner: JARVIS yine çalışır.
    """
    if not enabled:
        return VoiceIO(keyboard=keyboard, notify=notify, enabled=False)

    listener = None
    speaker = None
    try:
        import sys
        from pathlib import Path

        _scripts = str(Path(__file__).resolve().parents[1] / "scripts")
        if _scripts not in sys.path:
            sys.path.insert(0, _scripts)

        from j0_tts_adapters import EdgeTTSAdapter

        from voice.stt import FasterWhisperTranscriber, MicrophoneRecorder, VoiceListener

        listener = VoiceListener(
            recorder=MicrophoneRecorder(),
            transcriber=FasterWhisperTranscriber(model_size=whisper_model),
        )
        speaker = EdgeTTSAdapter(voice=tts_voice)
    except Exception as exc:  # noqa: BLE001
        if notify:
            notify(f"[ses] kurulamadı, klavye moduna geçildi: {exc}")
        return VoiceIO(keyboard=keyboard, notify=notify, enabled=False)

    return VoiceIO(
        listener=listener,
        speaker=speaker,
        keyboard=keyboard,
        notify=notify,
        enabled=True,
    )
