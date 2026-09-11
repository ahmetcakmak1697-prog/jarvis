"""
JARVIS M0 - Model Registry / Hardware Abstraction Layer
========================================================

Amac:
    Kod hicbir yerde dogrudan model adi ("mistral-nemo:latest") yazmasin.
    Bunun yerine ROL ister: local_main, local_small, research_model, vision_model...
    Hangi rolun hangi modele/back-end'e gittigini config/runtime_profiles.json belirler.

Neden:
    RTX 3070 -> 2x RTX 3090 gecisinde kodu yeniden yazmamak icin.
    Donanim yukseltmesi = tek satir profil degisikligi (active_profile),
    mimari kirilim degil.

Guvenlik / dayaniklilik:
    - Bu katman ASLA JarvisBrain'i dusurmez.
    - JSON yoksa, bozuksa, profil eksikse -> verilen fallback degeri doner.
    - Boylece mevcut sistem (MODEL = "mistral-nemo:latest") calismaya devam eder.

Kullanim:
    from agents.model_registry import ModelRegistry
    reg = ModelRegistry()
    model = reg.local_main(fallback="mistral-nemo:latest")
    backend = reg.backend()                # "ollama" / "vllm"
    url = reg.ollama_url()                  # "http://localhost:11434"
    prof = reg.active_profile_name()        # "rtx3070"

Not (M0 ileride buyuyecek):
    Bugun sadece rol cozumlemesi yapar. Yarin tensor_parallel_size,
    vision/stt/tts yonetimi, cloud_hybrid yonlendirme buraya eklenir.
"""

import json
from pathlib import Path


# Profil dosyasi proje kokunde: <root>/config/runtime_profiles.json
# Bu dosya <root>/agents/ altinda oldugu icin bir ust + config.
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "runtime_profiles.json"

# Profil hic okunamazsa son care: en azindan ollama varsay.
_HARD_FALLBACK_PROFILE = {
    "backend": "ollama",
    "ollama_url": "http://localhost:11434",
    "tensor_parallel_size": 1,
}


class ModelRegistry:
    """
    M0 - Runtime profil ve model rol cozumleyici.

    Tasarim ilkesi: 'fail safe, never crash'.
    Her metot, sorun olursa makul/verilen fallback dondurur.
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._data: dict = {}
        self._active: dict = {}
        self._loaded_ok: bool = False
        self._load()

    # ---------------- ic yukleme ----------------

    def _load(self) -> None:
        """runtime_profiles.json'u guvenli yukler. Hata olursa sessizce fallback'e duser."""
        try:
            if not self.config_path.exists():
                self._data = {}
                self._active = dict(_HARD_FALLBACK_PROFILE)
                self._loaded_ok = False
                return

            raw = self.config_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("runtime_profiles.json kok obje degil")

            self._data = data

            profiles = data.get("profiles", {})
            active_name = data.get("active_profile", "")

            active = profiles.get(active_name) if isinstance(profiles, dict) else None
            if not isinstance(active, dict):
                # active_profile gecersizse ilk profili dene, o da yoksa hard fallback.
                if isinstance(profiles, dict) and profiles:
                    first_key = next(iter(profiles))
                    candidate = profiles.get(first_key)
                    active = candidate if isinstance(candidate, dict) else dict(_HARD_FALLBACK_PROFILE)
                else:
                    active = dict(_HARD_FALLBACK_PROFILE)
                self._loaded_ok = False
            else:
                self._loaded_ok = True

            self._active = active

        except Exception:
            # Bilincli sessizlik: M0 cekirdegi dusuremez.
            self._data = {}
            self._active = dict(_HARD_FALLBACK_PROFILE)
            self._loaded_ok = False

    # ---------------- durum ----------------

    @property
    def loaded(self) -> bool:
        """Profil dosyasi gercekten dogru yuklendi mi?"""
        return self._loaded_ok

    def active_profile_name(self, fallback: str = "rtx3070") -> str:
        name = self._data.get("active_profile")
        return name if isinstance(name, str) and name else fallback

    def schema_version(self) -> int:
        try:
            return int(self._data.get("schema_version", 0))
        except Exception:
            return 0

    # ---------------- rol cozumleyiciler ----------------

    def _role(self, key: str, fallback: str = "") -> str:
        """Aktif profilden bir model rolunu cozer. Bos/eksikse fallback doner."""
        val = self._active.get(key)
        if isinstance(val, str) and val.strip() and not val.endswith("placeholder"):
            return val.strip()
        return fallback

    def local_main(self, fallback: str = "mistral-nemo:latest") -> str:
        """Ana sohbet modeli. En kritik rol; fallback mevcut calisan modeldir."""
        return self._role("local_main", fallback)

    def local_small(self, fallback: str = "") -> str:
        """Hizli/router modeli."""
        return self._role("local_small", fallback or self.local_main())

    def research_model(self, fallback: str = "") -> str:
        """Web arastirma sentezi icin model."""
        return self._role("research_model", fallback or self.local_main())

    def cloud_chat_model(self, fallback: str = "") -> str:
        """Sohbet metnini ureten DIS model. Bos ise bulut yolu kapalidir.

        CLAUDE.md 7.0: yerlesim ideolojiyle degil isin gereğiyle secilir;
        gunluk sohbet ve arastirma bulutta, ev kontrolu yerelde. Rol
        burada tanimli, adi profilde (KART_SES_YOLU_DEEPSEEK ADIM 1).
        """
        return self._role("cloud_chat_model", fallback)

    def cloud_chat_url(self, fallback: str = "") -> str:
        """Dis modelin OpenAI-uyumlu sohbet uc noktasi."""
        return self._role("cloud_chat_url", fallback)

    def cloud_chat_key_env(self, fallback: str = "") -> str:
        """Anahtarin ORTAM DEGISKENI ADI -- degeri degil, adi.

        Deger yalnizca ortamdan okunur; bu dosyaya ve hicbir loga yazilmaz
        (CLAUDE.md 9).
        """
        return self._role("cloud_chat_key_env", fallback)

    def vision_model(self, fallback: str = "") -> str:
        """Gorsel/multimodal model. Bos olabilir (henuz yok)."""
        return self._role("vision_model", fallback)

    def stt_model(self, fallback: str = "faster-whisper") -> str:
        return self._role("stt_model", fallback)

    def tts_model(self, fallback: str = "edge") -> str:
        return self._role("tts_model", fallback)

    # ---------------- back-end / altyapi ----------------

    def backend(self, fallback: str = "ollama") -> str:
        val = self._active.get("backend")
        return val if isinstance(val, str) and val.strip() else fallback

    def ollama_url(self, fallback: str = "http://localhost:11434") -> str:
        val = self._active.get("ollama_url")
        return val if isinstance(val, str) and val.strip() else fallback

    def tensor_parallel_size(self, fallback: int = 1) -> int:
        try:
            return int(self._active.get("tensor_parallel_size", fallback))
        except Exception:
            return fallback

    # ---------------- tani / ozet ----------------

    def summary(self) -> dict:
        """Dashboard/log icin guvenli ozet."""
        return {
            "loaded_ok": self._loaded_ok,
            "active_profile": self.active_profile_name(),
            "backend": self.backend(),
            "local_main": self.local_main(),
            "local_small": self.local_small(),
            "research_model": self.research_model(),
            "vision_model": self.vision_model() or "(yok)",
            "tensor_parallel_size": self.tensor_parallel_size(),
            "config_path": str(self.config_path),
        }


# Hizli manuel test:  python -m agents.model_registry
if __name__ == "__main__":
    reg = ModelRegistry()
    import json as _json
    print(_json.dumps(reg.summary(), ensure_ascii=False, indent=2))
    if not reg.loaded:
        print("[WARN] runtime_profiles.json tam yuklenemedi; fallback degerler kullaniliyor.")
    else:
        print("[OK] Profil yuklendi:", reg.active_profile_name())
