"""Mikrofon cihazi secimi JARVIS_MIC_DEVICE ile yapilabilmeli.

Canli testte JARVIS hic ses almadi (`stt_no_input: no_speech_detected`).
Sebep sagirlik degil, YANLIS KULAK: `MicrophoneRecorder(device=None)` isletim
sisteminin varsayilan giris aygitini kullaniyordu. Makinede iki mikrofon var --
HyperX Cloud III (kablosuz kulaklik, varsayilan) ve HyperX SoloCast (masaustu
USB kondenser) -- ve konusulan mikrofon varsayilan olan degildi.

Aygit indeksleri yeniden baglanmada degisir, bu yuzden isim parcasi da kabul
edilir: sounddevice `device` parametresinde alt-dize eslesmesi yapar.
"""
from __future__ import annotations

import pytest

from voice.stt import resolve_mic_device


@pytest.fixture(autouse=True)
def _temiz_ortam(monkeypatch):
    """Her test kendi ortam degiskenini kursun; gercek ortam sizmasin."""
    monkeypatch.delenv("JARVIS_MIC_DEVICE", raising=False)


def test_unset_falls_back_to_system_default(monkeypatch):
    """Degisken yoksa davranis degismemeli: None = isletim sistemi varsayilani."""
    assert resolve_mic_device() is None


@pytest.mark.parametrize("bos", ["", "   ", "\t"])
def test_blank_is_treated_as_unset(monkeypatch, bos):
    monkeypatch.setenv("JARVIS_MIC_DEVICE", bos)
    assert resolve_mic_device() is None


def test_name_fragment_is_passed_through(monkeypatch):
    """Isim parcasi tercih edilir: indeks yeniden baglanmada kayar, isim kaymaz."""
    monkeypatch.setenv("JARVIS_MIC_DEVICE", "SoloCast")
    assert resolve_mic_device() == "SoloCast"


def test_name_fragment_is_stripped(monkeypatch):
    monkeypatch.setenv("JARVIS_MIC_DEVICE", "  SoloCast  ")
    assert resolve_mic_device() == "SoloCast"


@pytest.mark.parametrize("ham,beklenen", [("2", 2), ("17", 17), (" 9 ", 9)])
def test_numeric_value_becomes_index(monkeypatch, ham, beklenen):
    """Tam sayi verilirse sounddevice aygit indeksi olarak gecmeli."""
    monkeypatch.setenv("JARVIS_MIC_DEVICE", ham)
    cozulen = resolve_mic_device()
    assert cozulen == beklenen
    assert isinstance(cozulen, int)


def test_negative_index_is_rejected_as_name(monkeypatch):
    """'-1' gecerli bir aygit indeksi degil; sayi gibi yorumlanmamali."""
    monkeypatch.setenv("JARVIS_MIC_DEVICE", "-1")
    assert resolve_mic_device() == "-1"


def test_recorder_defaults_to_resolved_device(monkeypatch):
    """Kayitci, acikca aygit verilmediginde ortamdan cozuleni kullanmali."""
    from voice.stt import MicrophoneRecorder

    monkeypatch.setenv("JARVIS_MIC_DEVICE", "SoloCast")
    assert MicrophoneRecorder()._device == "SoloCast"


def test_explicit_device_wins_over_env(monkeypatch):
    """Acik parametre ortami ezmeli; testler ortamdan etkilenmemeli."""
    from voice.stt import MicrophoneRecorder

    monkeypatch.setenv("JARVIS_MIC_DEVICE", "SoloCast")
    assert MicrophoneRecorder(device=3)._device == 3


def test_resolve_reads_env_at_call_time(monkeypatch):
    """Modul import aninda okunmamali; .env sonradan yuklenebiliyor."""
    monkeypatch.setenv("JARVIS_MIC_DEVICE", "Cloud III")
    assert resolve_mic_device() == "Cloud III"
    monkeypatch.setenv("JARVIS_MIC_DEVICE", "SoloCast")
    assert resolve_mic_device() == "SoloCast"
