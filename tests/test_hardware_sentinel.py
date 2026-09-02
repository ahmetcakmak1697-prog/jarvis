"""agents/hardware_sentinel.py sozlesmesi — donanim esikleri ve proaktif uyari.

Denetim raporundaki bosluk: metrik toplayicilari (tools/system_intelligence.py)
ZATEN vardi -- GPU sicakligi, RAM, CPU okunuyordu -- ama hicbir esik proaktif
cekirdege bagli degildi. Yani JARVIS sicakligi GOREBILIYOR ama fark
EDEMIYORDU. Bu modul o boslugu kapatir.

Okuyucu enjekte edilebilir: testler GPU olmadan, deterministik calisir.
"""
from __future__ import annotations

import pytest


def olcum(**kw):
    """Saglikli bir taban olcum; testler yalniz ilgilendigi alani ezer."""
    temel = {
        "gpu": {"available": True, "temperature": 55.0, "percent": 10.0,
                "memory_percent": 20.0},
        "ram": {"percent": 40.0, "used_gb": 12.0, "total_gb": 31.0},
        "cpu": 15.0,
    }
    temel.update(kw)
    return temel


def sentinel(metrikler=None, **kw):
    from agents.hardware_sentinel import HardwareSentinel

    veri = metrikler if metrikler is not None else olcum()
    return HardwareSentinel(reader=lambda: veri, **kw)


# --------------------------------------------------------------------------- #
# 1. Saglikli sistemde uyari YOK
# --------------------------------------------------------------------------- #

def test_healthy_system_produces_no_alerts():
    sonuc = sentinel().check()
    assert sonuc["ok"] is True
    assert sonuc["alerts"] == []
    assert sonuc["level"] == "ok"


def test_check_includes_raw_metrics():
    """Uyari yokken bile olcumler gorunur kalir -- panel bunlari gosterir."""
    sonuc = sentinel().check()
    assert sonuc["metrics"]["gpu"]["temperature"] == 55.0
    assert sonuc["metrics"]["cpu"] == 15.0


# --------------------------------------------------------------------------- #
# 2. GPU sicakligi — Ahmet'in verdigi ornek: 80 C uzeri kritik
# --------------------------------------------------------------------------- #

def test_gpu_over_80_is_critical():
    sonuc = sentinel(olcum(gpu={"available": True, "temperature": 82.0,
                                "percent": 90.0, "memory_percent": 50.0})).check()
    assert sonuc["level"] == "critical"
    uyari = next(a for a in sonuc["alerts"] if a["metric"] == "gpu_temperature")
    assert uyari["level"] == "critical"
    assert uyari["value"] == 82.0
    assert "82" in uyari["message"]


def test_gpu_warm_but_not_critical_is_warning():
    sonuc = sentinel(olcum(gpu={"available": True, "temperature": 77.0,
                                "percent": 60.0, "memory_percent": 40.0})).check()
    assert sonuc["level"] == "warn"
    assert sonuc["alerts"][0]["level"] == "warn"


def test_gpu_at_exact_threshold_is_critical():
    """Esik DAHILDIR: 80.0 kritik sayilir, 'tam esikte sustu' olmaz."""
    sonuc = sentinel(olcum(gpu={"available": True, "temperature": 80.0,
                                "percent": 50.0, "memory_percent": 30.0})).check()
    assert sonuc["level"] == "critical"


def test_missing_gpu_produces_no_false_alarm():
    """GPU yoksa uyari uretme -- yoklugu ariza sayma."""
    sonuc = sentinel(olcum(gpu={"available": False})).check()
    assert sonuc["alerts"] == []
    assert sonuc["level"] == "ok"


# --------------------------------------------------------------------------- #
# 3. RAM ve CPU
# --------------------------------------------------------------------------- #

def test_high_ram_is_critical():
    sonuc = sentinel(olcum(ram={"percent": 95.0, "used_gb": 29.5,
                                "total_gb": 31.0})).check()
    assert sonuc["level"] == "critical"
    assert any(a["metric"] == "ram_percent" for a in sonuc["alerts"])


def test_high_cpu_is_warning():
    sonuc = sentinel(olcum(cpu=92.0)).check()
    assert any(a["metric"] == "cpu_percent" for a in sonuc["alerts"])


def test_multiple_alerts_report_worst_level():
    sonuc = sentinel(olcum(
        gpu={"available": True, "temperature": 83.0, "percent": 99.0,
             "memory_percent": 97.0},
        ram={"percent": 88.0, "used_gb": 27.0, "total_gb": 31.0},
    )).check()
    assert sonuc["level"] == "critical"
    assert len(sonuc["alerts"]) >= 2


# --------------------------------------------------------------------------- #
# 4. Mesajlar Turkce ve JARVIS agzindan
# --------------------------------------------------------------------------- #

def test_messages_are_turkish_and_addressed():
    sonuc = sentinel(olcum(gpu={"available": True, "temperature": 84.0,
                                "percent": 95.0, "memory_percent": 60.0})).check()
    mesaj = sonuc["alerts"][0]["message"]
    assert "Efendim" in mesaj
    assert "°C" in mesaj or "derece" in mesaj


def test_spoken_summary_is_short_enough_to_say_aloud():
    sonuc = sentinel(olcum(gpu={"available": True, "temperature": 84.0,
                                "percent": 95.0, "memory_percent": 60.0})).check()
    assert 0 < len(sonuc["spoken"]) <= 200


def test_spoken_summary_is_empty_when_healthy():
    assert sentinel().check()["spoken"] == ""


# --------------------------------------------------------------------------- #
# 5. Tekrar bastirma — ayni uyari her turda tekrarlanmaz
# --------------------------------------------------------------------------- #

def test_same_alert_is_not_repeated_within_cooldown():
    from agents.hardware_sentinel import HardwareSentinel

    sicak = olcum(gpu={"available": True, "temperature": 85.0,
                       "percent": 99.0, "memory_percent": 70.0})
    saat = {"t": 1000.0}
    s = HardwareSentinel(reader=lambda: sicak, clock=lambda: saat["t"],
                         cooldown_s=300.0)

    assert s.check()["should_notify"] is True, "ilk uyari bildirilmeli"
    saat["t"] += 10
    assert s.check()["should_notify"] is False, "10sn sonra tekrar bildirilmemeli"
    saat["t"] += 400
    assert s.check()["should_notify"] is True, "cooldown sonrasi tekrar bildirilmeli"


def test_escalation_breaks_cooldown():
    """warn -> critical yukselmesi cooldown'i deler: durum kotulesti."""
    from agents.hardware_sentinel import HardwareSentinel

    durum = {"m": olcum(gpu={"available": True, "temperature": 77.0,
                             "percent": 60.0, "memory_percent": 40.0})}
    saat = {"t": 0.0}
    s = HardwareSentinel(reader=lambda: durum["m"], clock=lambda: saat["t"],
                         cooldown_s=300.0)

    assert s.check()["should_notify"] is True
    saat["t"] += 5
    durum["m"] = olcum(gpu={"available": True, "temperature": 85.0,
                            "percent": 99.0, "memory_percent": 70.0})
    assert s.check()["should_notify"] is True, "kotulesme bildirilmeli"


def test_recovery_is_reported_once():
    """Kritikten normale donus bir kez bildirilir."""
    from agents.hardware_sentinel import HardwareSentinel

    durum = {"m": olcum(gpu={"available": True, "temperature": 85.0,
                             "percent": 99.0, "memory_percent": 70.0})}
    saat = {"t": 0.0}
    s = HardwareSentinel(reader=lambda: durum["m"], clock=lambda: saat["t"])
    s.check()
    durum["m"] = olcum()
    sonuc = s.check()
    assert sonuc["level"] == "ok"
    assert sonuc["recovered"] is True
    assert s.check()["recovered"] is False, "toparlanma yalniz bir kez"


# --------------------------------------------------------------------------- #
# 6. Dayaniklilik
# --------------------------------------------------------------------------- #

def test_reader_failure_does_not_raise():
    from agents.hardware_sentinel import HardwareSentinel

    def patlayan():
        raise RuntimeError("nvidia-smi yok")

    sonuc = HardwareSentinel(reader=patlayan).check()
    assert sonuc["ok"] is False
    assert sonuc["alerts"] == []
    assert "nvidia-smi yok" in (sonuc["error"] or "")


def test_malformed_metrics_do_not_raise():
    sonuc = sentinel({"gpu": None, "ram": "bozuk", "cpu": None}).check()
    assert sonuc["alerts"] == []


def test_default_reader_is_lazy():
    """Modulu import etmek nvidia-smi CALISTIRMAMALI."""
    import ast
    from pathlib import Path

    kaynak = (Path(__file__).resolve().parents[1]
              / "agents" / "hardware_sentinel.py").read_text(encoding="utf-8")
    ust = set()
    for node in ast.parse(kaynak).body:
        if isinstance(node, ast.Import):
            ust.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            ust.add(node.module.split(".")[0])
    assert "tools" not in ust, "tools.system_intelligence tembel import edilmeli"


@pytest.mark.parametrize("sicaklik", [0.0, -1.0, None, "sicak"])
def test_absurd_temperature_values_are_ignored(sicaklik):
    sonuc = sentinel(olcum(gpu={"available": True, "temperature": sicaklik,
                                "percent": 10.0, "memory_percent": 10.0})).check()
    assert not any(a["metric"] == "gpu_temperature" for a in sonuc["alerts"])
