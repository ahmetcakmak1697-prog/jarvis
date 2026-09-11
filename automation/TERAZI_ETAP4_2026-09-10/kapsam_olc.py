"""Replay recorded answers and mechanically audit ETAP 4 corpus loss.

Run from the repository root with PYTHONPATH set to that root. No model calls.
The historical scores are kept separate from the pre-change detector scores.
"""

import hashlib
import json
from pathlib import Path

from eval import quality_scorer as scorer
from eval.run_turkish_quality import load_cases


def main():
    out = Path(__file__).resolve().parent
    before = json.loads((out / "once.json").read_text(encoding="utf-8"))
    old = set(before["old_ngrams"])
    new = set(scorer._LEAK_NGRAMS)
    lost = old - new
    expected = set(before["method_ngrams"])
    cases = {case["id"]: case for case in load_cases()}
    flips = []
    current_flips = []
    rescored = []
    sources_unchanged = []
    for run in before["recorded_runs"]:
        path = Path(run["file"])
        raw = path.read_bytes()
        sources_unchanged.append(hashlib.sha256(raw).hexdigest() == run["sha256"])
        data = json.loads(raw)
        old_rows = {row["id"]: row for row in run["scores"]}
        for row in data["results"]:
            case_id = row["id"]
            score = scorer.score_answer(row.get("answer"), cases[case_id])
            rescored.append({"file": run["file"], "id": case_id, "score": score})
            for key, destination in (("stored_score", flips),
                                     ("current_score", current_flips)):
                previous = old_rows[case_id][key]
                if previous.get("prompt_leak") is True and score["prompt_leak"] is False:
                    hits = previous["prompt_leak_hits"]
                    destination.append({
                        "file": run["file"], "id": case_id,
                        "old_hits": hits, "new_hits": score["prompt_leak_hits"],
                        "old_hits_subset_of_lost": set(hits) <= lost,
                        "outside_lost": sorted(set(hits) - lost),
                    })
    persona_hash = hashlib.sha256(Path("agents/persona.py").read_bytes()).hexdigest()
    checks = {
        "persona_unchanged": persona_hash == before["source_sha256"]["agents\\persona.py"],
        "recorded_sources_unchanged": all(sources_unchanged),
        "lost_equals_method_ngrams": lost == expected,
        "no_added_ngrams": not (new - old),
        "historical_flip_hits_subset_of_lost": all(
            flip["old_hits_subset_of_lost"] for flip in flips),
        "current_flip_hits_subset_of_lost": all(
            flip["old_hits_subset_of_lost"] for flip in current_flips),
    }
    result = {
        "schema_version": 1, "checks": checks,
        "old_count": len(old), "new_count": len(new),
        "lost_ngrams": sorted(lost), "added_ngrams": sorted(new - old),
        "unexpected_loss": sorted(lost - expected),
        "missing_loss": sorted(expected - lost),
        "historical_true_to_false": flips,
        "current_true_to_false": current_flips,
        "rescored": rescored,
    }
    (out / "sonra.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "checks": checks, "old": len(old), "new": len(new), "lost": len(lost),
        "recorded_runs": len(before["recorded_runs"]), "answers": len(rescored),
        "historical_flips": len(flips), "current_flips": len(current_flips),
        "violations": [flip for flip in flips if not flip["old_hits_subset_of_lost"]],
    }, ensure_ascii=False, indent=2))
    assert all(checks.values()), "ETAP 4 mechanical coverage check failed; STOP"


if __name__ == "__main__":
    main()
