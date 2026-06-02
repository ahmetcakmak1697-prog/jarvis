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


def test_next_action_planner_recommends_c2_4_for_current_state():
    planner = NextActionPlanner()
    plan = planner.plan()

    assert plan.recommended_action == "C2.4 next-action planner"
    assert plan.current_phase == "C2"
    assert plan.confidence >= 90
    assert plan.acceptance_criteria


def test_next_action_planner_acceptance_criteria_mentions_tests_and_smoke():
    planner = NextActionPlanner()
    plan = planner.plan()

    joined = "\n".join(plan.acceptance_criteria).lower()

    assert "planner has tests" in joined
    assert "c2 smoke suite" in joined
    assert "no llm call" in joined


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
