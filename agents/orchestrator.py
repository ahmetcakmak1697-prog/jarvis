"""
Multi-LLM Orchestrator
Önce küçük modeli dene → güven düşükse büyüğüne yükselt
RTX 3070'de mantıklı dengede çalışır
"""
import requests


class LLMOrchestrator:
    LADDER = [
        ("llama3.2", 0.55, "fast"),           # Hızlı, basit
        ("mistral-nemo:latest", 0.70, "mid"), # Ana model
    ]

    def __init__(self, available_models=None):
        self.available = available_models or []

    def _is_available(self, model_name: str) -> bool:
        if not self.available:
            return True
        prefix = model_name.split(":")[0].lower()
        return any(prefix in a.lower() for a in self.available)

    def _gen(self, model: str, prompt: str, options: dict = None) -> dict:
        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False,
                      "options": options or {"temperature": 0.5, "num_predict": 300}},
                timeout=120)
            data = r.json()
            return {
                "response": data.get("response", "").strip(),
                "model": model,
                "ok": True
            }
        except Exception as e:
            return {"response": "", "model": model, "ok": False, "error": str(e)}

    def _check_confidence(self, response: str) -> float:
        """0.0-1.0: Cevap ne kadar emin?"""
        if not response or len(response) < 20:
            return 0.0
        uncertain = ["bilmiyorum", "emin değilim", "muhtemelen", "sanırım",
                     "tahminen", "belki", "olabilir", "araştırmalıyım"]
        text = response.lower()
        if any(u in text for u in uncertain):
            return 0.3
        if len(response) > 100:
            return 0.8
        return 0.6

    def chat(self, prompt: str, force_model: str = None) -> dict:
        """Akıllı yükseltme ile cevap üret"""
        if force_model:
            return self._gen(force_model, prompt)

        attempts = []
        for model, threshold, tier in self.LADDER:
            if not self._is_available(model):
                continue
            result = self._gen(model, prompt)
            if not result["ok"]:
                attempts.append({"model": model, "ok": False})
                continue

            conf = self._check_confidence(result["response"])
            result["confidence"] = conf
            result["tier"] = tier
            attempts.append({"model": model, "confidence": conf})

            if conf >= threshold:
                result["attempts"] = attempts
                return result

        # Yetmedi, son cevabı dön
        result["attempts"] = attempts
        result["escalated"] = True
        return result
