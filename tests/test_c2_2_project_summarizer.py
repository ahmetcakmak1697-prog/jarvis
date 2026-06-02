"""C2.2 Project summarizer tests."""

from __future__ import annotations

from agents.project_summarizer import ProjectSummarizer, ProjectSummary


def test_project_summarizer_returns_summary_dataclass():
    summarizer = ProjectSummarizer()
    summary = summarizer.summarize()

    assert isinstance(summary, ProjectSummary)
    assert summary.project == "Jarvis v5"
    assert summary.current_phase == "C2"
    assert summary.last_completed_phase == "C1"
    assert summary.branch
    assert isinstance(summary.git_clean, bool)
    assert summary.last_checkpoint == "docs/C1_MEMORY_CHECKPOINT.md"
    assert isinstance(summary.next_steps, list)
    assert isinstance(summary.recent_commits, list)
    assert isinstance(summary.docs_present, dict)
    assert isinstance(summary.risks, list)


def test_project_summarizer_detects_required_docs():
    summarizer = ProjectSummarizer()
    summary = summarizer.summarize()

    assert summary.docs_present["master_roadmap"] is True
    assert summary.docs_present["c1_checkpoint"] is True
    assert summary.docs_present["engineering_standards"] is True


def test_project_summary_text_contains_core_fields():
    summarizer = ProjectSummarizer()
    text = summarizer.summary_text()

    assert "Project Intelligence Summary" in text
    assert "Project: Jarvis v5" in text
    assert "Current phase: C2" in text
    assert "Last completed phase: C1" in text
    assert "Git clean:" in text
    assert "Documents:" in text
    assert "Next steps:" in text
    assert "Risk notes:" in text


def test_project_summary_to_dict_shape():
    summarizer = ProjectSummarizer()
    data = summarizer.summarize().to_dict()

    assert data["project"] == "Jarvis v5"
    assert data["current_phase"] == "C2"
    assert data["last_completed_phase"] == "C1"
    assert "docs_present" in data
    assert "recent_commits" in data
    assert "risks" in data
