"""Self-Improver - Observe → Reflect → Optimize."""
import json
import requests
from pathlib import Path
from datetime import datetime
from collections import Counter


class SelfImprover:
    def __init__(self, model="mistral-nemo:latest"):
        self.conv_path = Path("memory/conversations.json")
        self.insights_path = Path("memory/improvements.json")
        self.reports_dir = Path("logs/improvement_reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.model = model

    def analyze_weaknesses(self):
        if not self.conv_path.exists():
            return {"status": "no_data"}
        convs = json.loads(self.conv_path.read_text(encoding='utf-8'))
        ev = [c for c in convs if c.get("metadata", {}).get("evaluated")]
        if len(ev) < 3:
            return {"status": "insufficient", "count": len(ev)}
        weak = [c for c in ev if c["metadata"].get("quality_score", 5) < 5]
        if len(weak) < 1:
            return {"status": "no_weakness"}
        issues = []
        for c in weak:
            issues.extend(c["metadata"].get("eval_issues", []))
        top_issues = Counter(issues).most_common(5)
        samples = "\n\n".join(self._fmt(c) for c in weak[:5])
        prompt = f"""JARVIS'in düşük puan aldığı cevaplar:

{samples}

Pattern bul. SADECE JSON döndür:
{{
  "ana_zayıflık": "<en büyük sorun>",
  "ortak_pattern": "<davranış>",
  "öneri": "<nasıl düzelmeli>",
  "araştırılacak_konular": ["<k1>", "<k2>"],
  "kullanıcıya_soru": "<somut 1 soru>"
}}"""
        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "stream": False, "format": "json",
                      "options": {"temperature": 0.3, "num_predict": 500}},
                timeout=120)
            analysis = json.loads(r.json().get("response", "{}"))
        except Exception as e:
            return {"status": "error", "msg": str(e)[:100]}
        report = {
            "timestamp": datetime.now().isoformat(),
            "weak_count": len(weak), "evaluated_count": len(ev),
            "weakness_rate": round(len(weak) / len(ev) * 100, 1),
            "top_issues": [{"issue": i, "count": c} for i, c in top_issues],
            "analysis": analysis
        }
        self._save(report)
        rf = self.reports_dir / f"r_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        rf.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                      encoding='utf-8')
        return report

    def _fmt(self, conv):
        msgs = conv.get("messages", [])
        u = next((m["content"] for m in msgs if m["role"] == "user"), "")
        a = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
        m = conv.get("metadata", {})
        return (f"S: {u}\nC: {a}\nP: {m.get('quality_score', 0)}/10\n"
                f"Sorun: {m.get('eval_reason', '')}")

    def _save(self, report):
        ins = []
        if self.insights_path.exists():
            try:
                ins = json.loads(self.insights_path.read_text(encoding='utf-8'))
            except:
                pass
        ins.append(report)
        ins = ins[-30:]
        self.insights_path.write_text(
            json.dumps(ins, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_pending_question(self):
        if not self.insights_path.exists():
            return ""
        try:
            ins = json.loads(self.insights_path.read_text(encoding='utf-8'))
            if ins:
                return ins[-1].get("analysis", {}).get("kullanıcıya_soru", "")
        except:
            pass
        return ""

    def get_latest_report(self):
        if not self.insights_path.exists():
            return {}
        try:
            ins = json.loads(self.insights_path.read_text(encoding='utf-8'))
            return ins[-1] if ins else {}
        except:
            return {}
