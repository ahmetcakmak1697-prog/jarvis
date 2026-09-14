"""Quality Evaluator - LLM scores its own answers."""
import json
import requests
import re


MODEL = "mistral-nemo:latest"

EVAL = """Konuşmayı 1-10 puanla.

KULLANICI: {u}
ASİSTAN: {j}

Kriterler: Türkçe doğruluğu, anlam, kalite, JARVIS karakteri.
SADECE JSON:
{{
  "score": <1-10>,
  "reason": "<tek cümle>",
  "issues": ["<s1>"],
  "strengths": ["<g1>"]
}}"""


def evaluate(user_msg, jarvis_msg):
    p = EVAL.format(u=user_msg, j=jarvis_msg)
    try:
        r = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": MODEL, "prompt": p, "stream": False,
                  "format": "json",
                  "options": {"temperature": 0.2, "num_predict": 200}},
            timeout=60)
        resp = r.json().get("response", "").strip()
        resp = re.sub(r"```(?:json)?", "", resp).strip()
        d = json.loads(resp)
        score = max(1, min(10, int(d.get("score", 5))))
        return {
            "score": score,
            "reason": d.get("reason", ""),
            "issues": d.get("issues", []),
            "strengths": d.get("strengths", []),
            "evaluated": True
        }
    except Exception as e:
        return {
            "score": 5, "reason": f"Hata: {str(e)[:80]}",
            "issues": [], "strengths": [], "evaluated": False
        }


def evaluate_batch(conversations, verbose=True):
    total = len(conversations)
    for i, conv in enumerate(conversations, 1):
        if conv.get("metadata", {}).get("evaluated"):
            continue
        msgs = conv.get("messages", [])
        u = next((m["content"] for m in msgs if m["role"] == "user"), "")
        j = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
        if not u or not j:
            continue
        if verbose:
            print(f"[{i}/{total}] {u[:50]}...")
        ev = evaluate(u, j)
        if "metadata" not in conv:
            conv["metadata"] = {}
        conv["metadata"]["quality_score"] = ev["score"]
        conv["metadata"]["eval_reason"] = ev["reason"]
        conv["metadata"]["eval_issues"] = ev["issues"]
        conv["metadata"]["eval_strengths"] = ev["strengths"]
        conv["metadata"]["evaluated"] = ev["evaluated"]
        if verbose:
            print(f"  → {ev['score']}/10")
    return conversations


if __name__ == "__main__":
    print(json.dumps(evaluate("Adın ne?", "Adım JARVIS efendim."),
                     ensure_ascii=False, indent=2))
