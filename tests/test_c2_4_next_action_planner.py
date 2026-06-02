"""C2.4 Next action planner tests."""

from __future__ import annotations

from agents.next_action_planner import NextActionPlanner, NextActionPlan


def test_next_action_planner_returns_plan_dataclass():
    planner = NextActionPlanner()
    plan = planner.plan()

    assert isinstance(plan, NextActionPlan)
    assert plan.recommended_action
    assert plan.reason
    assert plan.current_phase == "C2"
    assert plan.next_phase
    assert isinstance(plan.confidence, int)
    assert isinstance(plan.git_clean, bool)
    assert isinstance(plan.acceptance_criteria, list)
    assert isinstance(plan.risks, list)
    assert isinstance(plan.evidence, list)


def test_next_action_planner_recommends_valid_c2_action_for_current_state():
    planner = NextActionPlanner()
    plan = planner.plan()

    assert plan.recommended_action.startswith("C2.")
    assert plan.recommended_action != "unknown"
    assert plan.current_phase == "C2"
    assert plan.confidence >= 90
    assert plan.acceptance_criteria


def test_next_action_planner_acceptance_criteria_are_useful():
    planner = NextActionPlanner()
    plan = planner.plan()

    joined = "\n".join(plan.acceptance_criteria).lower()

    assert len(plan.acceptance_criteria) >= 3
    assert any(
        token in joined
        for token in ["test", "tests", "smoke", "git status", "command", "passes"]
    )
    assert plan.recommended_action.startswith("C2.")


def test_next_action_summary_text_contains_core_fields():
    planner = NextActionPlanner()
    text = planner.summary_text()

    assert "Next Action Plan" in text
    assert "Recommended action:" in text
    assert "Reason:" in text
    assert "Current phase: C2" in text
    assert "Confidence:" in text
    assert "Acceptance criteria:" in text
    assert "Evidence:" in text


def test_next_action_plan_to_dict_shape():
    planner = NextActionPlanner()
    data = planner.plan().to_dict()

    assert "recommended_action" in data
    assert "reason" in data
    assert "current_phase" in data
    assert "next_phase" in data
    assert "confidence" in data
    assert "acceptance_criteria" in data
    assert "risks" in data
    assert "evidence" in data
