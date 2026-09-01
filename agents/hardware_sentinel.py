"""agents/hardware_sentinel.py — donanım eşikleri ve proaktif uyarı üretimi.

Eşik 4/5'in çekirdeği. Denetim raporundaki boşluk şuydu: metrik toplayıcıları
`tools/system_intelligence.py` içinde **zaten vardı** — GPU sıcaklığı, RAM ve
CPU okunuyordu — ama hiçbir eşik proaktif çekirdeğe bağlı değildi. Yani JARVIS
sıcaklığı *görebiliyor* ama *fark edemiyordu*. Bu modül o boşluğu kapatır.

Tasarım:

* **Okuyucu enjekte edilebilir.** Testler GPU olmadan, deterministik çalışır.
  `tools.system_intelligence` yalnızca varsayılan okuyucunun içinde, tembel
  import edilir — bu modülü import etmek `nvidia-smi` çalıştırmaz.
* **Sessiz kalmak da bir karar.** GPU yoksa uyarı üretilmez; yokluk arıza
  değildir. Saçma değerler (0, negatif, None, metin) yok sayılır — bozuk
  sensör okuması yanlış alarma dönüşmemeli.
* **Tekrar bastırma.** Aynı uyarı her turda tekrarlanmaz; `cooldown_s`
  süresince susar. Ama durum **kötüleşirse** (warn → critical) cooldown
  delinir: kötüleşme her zaman duyurulur.
* **Toparlanma bir kez bildirilir.** Kritikten normale dönüş sessizce
  geçilmez, ama sürekli de tekrarlanmaz.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Threshold", "DEFAULT_THRESHOLDS", "HardwareSentinel"]


@dataclass(frozen=True)
class Threshold:
    """Uyarı ve kritik eşikleri. Eşik değeri **dahildir** (>=)."""

    warn: float
    critical: float


#: Varsayılan eşikler. GPU 80 °C sınırı Ahmet'in verdiği örnektir; RTX 3070
#: için 83 °C üretici sınırına yakındır, 80 makul bir erken uyarıdır.
DEFAULT_THRESHOLDS: Dict[str, Threshold] = {
    "gpu_temperature": Threshold(warn=75.0, critical=80.0),
    "gpu_memory_percent": Threshold(warn=85.0, critical=95.0),
    "ram_percent": Threshold(warn=85.0, critical=93.0),
    "cpu_percent": Threshold(warn=90.0, critical=97.0),
}

_ETIKET = {
    "gpu_temperature": ("GPU sıcaklığı", "°C"),
    "gpu_memory_percent": ("GPU belleği", "%"),
    "ram_percent": ("Sistem belleği", "%"),
    "cpu_percent": ("İşlemci yükü", "%"),
}

_SEVIYE_SIRASI = {"ok": 0, "warn": 1, "critical": 2}


def _sayi(deger: Any) -> Optional[float]:
    """Değeri anlamlı bir ölçüme çevirir; olmuyorsa None.

    Bozuk sensör okuması (None, metin, 0, negatif) yanlış alarma dönüşmemeli:
    0 °C bir GPU sıcaklığı değil, okunamamış bir değerdir.
    """
    if isinstance(deger, bool) or deger is None:
        return None
    try:
        sayi = float(deger)
    except (TypeError, ValueError):
        return None
    if sayi <= 0:
        return None
    return sayi


class HardwareSentinel:
    """Donanım metriklerini okur, eşiklere vurur, uyarı üretir."""

    def __init__(
        self,
        reader: Optional[Callable[[], Dict[str, Any]]] = None,
        thresholds: Optional[Dict[str, Threshold]] = None,
        clock: Optional[Callable[[], float]] = None,
        cooldown_s: float = 300.0,
    ) -> None:
        self._reader = reader
        self._thresholds = dict(thresholds or DEFAULT_THRESHOLDS)
        self._clock = clock or time.monotonic
        self._cooldown_s = cooldown_s
        self._son_bildirim: Dict[str, float] = {}
        self._son_seviye: Dict[str, str] = {}
        self._onceki_genel = "ok"
        self._toparlanma_bildirildi = True

    # ------------------------------------------------------------------ #

    def read(self) -> Dict[str, Any]:
        if self._reader is not None:
            return self._reader()
        return self._default_reader()

    @staticmethod
    def _default_reader() -> Dict[str, Any]:
        """Gerçek metrikler. `tools` tembel import edilir."""
        from tools.system_intelligence import (
            _get_cpu_percent,
            _get_gpu_info,
            _get_ram_info,
        )

        return {
            "gpu": _get_gpu_info(),
            "ram": _get_ram_info(),
            "cpu": _get_cpu_percent(),
        }

    # ------------------------------------------------------------------ #

    def _degerler(self, metrikler: Dict[str, Any]) -> Dict[str, float]:
        gpu = metrikler.get("gpu") if isinstance(metrikler.get("gpu"), dict) else {}
        ram = metrikler.get("ram") if isinstance(metrikler.get("ram"), dict) else {}

        degerler: Dict[str, float] = {}
        if gpu.get("available"):
            for anahtar, alan in (("gpu_temperature", "temperature"),
                                  ("gpu_memory_percent", "memory_percent")):
                sayi = _sayi(gpu.get(alan))
                if sayi is not None:
                    degerler[anahtar] = sayi

        sayi = _sayi(ram.get("percent"))
        if sayi is not None:
            degerler["ram_percent"] = sayi

        sayi = _sayi(metrikler.get("cpu"))
        if sayi is not None:
            degerler["cpu_percent"] = sayi

        return degerler

    def _uyarilar(self, degerler: Dict[str, float]) -> List[Dict[str, Any]]:
        uyarilar: List[Dict[str, Any]] = []
        for metrik, deger in degerler.items():
            esik = self._thresholds.get(metrik)
            if esik is None:
                continue
            if deger >= esik.critical:
                seviye, sinir = "critical", esik.critical
            elif deger >= esik.warn:
                seviye, sinir = "warn", esik.warn
            else:
                continue
            ad, birim = _ETIKET.get(metrik, (metrik, ""))
            gosterim = f"{deger:.0f}{birim}" if birim else f"{deger:.0f}"
            nitel = "kritik seviyede" if seviye == "critical" else "yükseliyor"
            uyarilar.append({
                "metric": metrik,
                "level": seviye,
                "value": deger,
                "threshold": sinir,
                "message": f"Efendim, {ad} {nitel}: {gosterim}.",
            })
        uyarilar.sort(key=lambda u: (-_SEVIYE_SIRASI[u["level"]], u["metric"]))
        return uyarilar

    def _bildirilmeli_mi(self, uyarilar: List[Dict[str, Any]]) -> bool:
        simdi = self._clock()
        bildir = False
        for uyari in uyarilar:
            metrik = uyari["metric"]
            onceki = self._son_seviye.get(metrik)
            kotulesti = (
                onceki is not None
                and _SEVIYE_SIRASI[uyari["level"]] > _SEVIYE_SIRASI[onceki]
            )
            son = self._son_bildirim.get(metrik)
            sogumus = son is None or (simdi - son) >= self._cooldown_s
            if kotulesti or sogumus:
                bildir = True
                self._son_bildirim[metrik] = simdi
            self._son_seviye[metrik] = uyari["level"]

        aktif = {u["metric"] for u in uyarilar}
        for metrik in list(self._son_seviye):
            if metrik not in aktif:
                self._son_seviye.pop(metrik, None)
                self._son_bildirim.pop(metrik, None)
        return bildir

    def check(self) -> Dict[str, Any]:
        """Bir ölçüm turu: oku, eşiklere vur, bildirim kararını ver."""
        try:
            metrikler = self.read()
        except Exception as exc:  # noqa: BLE001 - yüzeye çıkar, yutulmaz
            return {
                "ok": False, "error": str(exc), "metrics": {},
                "alerts": [], "level": "ok", "spoken": "",
                "should_notify": False, "recovered": False,
            }

        if not isinstance(metrikler, dict):
            metrikler = {}

        uyarilar = self._uyarilar(self._degerler(metrikler))
        seviye = "ok"
        for uyari in uyarilar:
            if _SEVIYE_SIRASI[uyari["level"]] > _SEVIYE_SIRASI[seviye]:
                seviye = uyari["level"]

        bildir = self._bildirilmeli_mi(uyarilar)

        toparlandi = False
        if seviye == "ok" and self._onceki_genel != "ok":
            toparlandi = True
            self._toparlanma_bildirildi = False
        elif seviye == "ok" and not self._toparlanma_bildirildi:
            self._toparlanma_bildirildi = True
        self._onceki_genel = seviye

        return {
            "ok": True,
            "error": None,
            "metrics": metrikler,
            "alerts": uyarilar,
            "level": seviye,
            "spoken": uyarilar[0]["message"] if uyarilar else "",
            "should_notify": bildir,
            "recovered": toparlandi,
        }
