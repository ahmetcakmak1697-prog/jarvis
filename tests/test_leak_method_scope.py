"""ETAP 4: following the requested answer structure is not prompt leakage."""

from eval.quality_scorer import score_answer


def test_requested_risk_test_rollback_heading_is_not_a_leak():
    answer = "### 6. Risk, Test ve Geri Alma Yolu"
    score = score_answer(answer, {})
    assert score["prompt_leak"] is False, score["prompt_leak_hits"]


def test_identity_instruction_still_leaks_beside_requested_heading():
    answer = (
        "### 6. Risk, Test ve Geri Alma Yolu\n"
        "Reaktif de\u011fil, proaktifsin."
    )
    score = score_answer(answer, {})
    assert score["prompt_leak"] is True
    assert "reaktif degil proaktifsin" in score["prompt_leak_hits"]
