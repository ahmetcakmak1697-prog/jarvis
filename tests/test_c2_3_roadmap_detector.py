"""C2.3 Roadmap detector tests."""

from __future__ import annotations

from agents.roadmap_detector import RoadmapDetector, RoadmapPosition


def test_roadmap_detector_returns_position_dataclass():
    detector = RoadmapDetector()
    pos = detector.detect()

    assert isinstance(pos, RoadmapPosition)
    assert pos.current_phase == "C2"
    assert pos.last_completed_phase == "C1"
    assert pos.next_phase
    assert isinstance(pos.roadmap_exists, bool)
    assert isinstance(pos.c1_checkpoint_exists, bool)
    assert isinstance(pos.project_state_exists, bool)
    assert isinstance(pos.git_clean, bool)
    assert isinstance(pos.confidence, int)
    assert isinstance(pos.evidence, list)
    assert isinstance(pos.risks, list)


def test_roadmap_detector_detects_required_docs():
    detector = RoadmapDetector()
    pos = detector.detect()

    assert pos.roadmap_exists is True
    assert pos.c1_checkpoint_exists is True
    assert pos.project_state_exists is True


def test_roadmap_detector_infers_c2_3_after_c2_2_commits():
    detector = RoadmapDetector()
    pos = detector.detect()

    assert pos.current_phase == "C2"
    assert pos.last_completed_phase == "C1"
    assert pos.next_phase == "C2.3 current roadmap detector"
    assert pos.confidence >= 90


def test_roadmap_summary_text_contains_core_fields():
    detector = RoadmapDetector()
    text = detector.summary_text()

    assert "Roadmap Position" in text
    assert "Current phase: C2" in text
    assert "Last completed phase: C1" in text
    assert "Next phase:" in text
    assert "Confidence:" in text
    assert "Evidence:" in text


def test_roadmap_position_to_dict_shape():
    detector = RoadmapDetector()
    data = detector.detect().to_dict()

    assert data["current_phase"] == "C2"
    assert data["last_completed_phase"] == "C1"
    assert "next_phase" in data
    assert "confidence" in data
    assert "evidence" in data
    assert "risks" in data
