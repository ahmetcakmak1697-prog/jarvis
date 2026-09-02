"""D2 — Web research composition flag tests."""
from __future__ import annotations

import os


def _import_helper():
    from tools.telegram_agent import _web_research_enabled_from_env, _build_assistant_executor
    return _web_research_enabled_from_env, _build_assistant_executor


def test_flag_disabled_by_default():
    enabled_fn, _ = _import_helper()
    # Ensure env is clean
    saved = os.environ.pop("JARVIS_WEB_RESEARCH_ENABLED", None)
    try:
        assert enabled_fn() is False
    finally:
        if saved is not None:
            os.environ["JARVIS_WEB_RESEARCH_ENABLED"] = saved


def test_flag_disabled_explicit_zero():
    enabled_fn, _ = _import_helper()
    os.environ["JARVIS_WEB_RESEARCH_ENABLED"] = "0"
    try:
        assert enabled_fn() is False
    finally:
        del os.environ["JARVIS_WEB_RESEARCH_ENABLED"]


def test_flag_enabled_values():
    enabled_fn, _ = _import_helper()
    for val in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
        os.environ["JARVIS_WEB_RESEARCH_ENABLED"] = val
        try:
            assert enabled_fn() is True, f"value={val!r} should enable"
        finally:
            del os.environ["JARVIS_WEB_RESEARCH_ENABLED"]


def test_build_disabled_no_web_research_classes():
    _, build_fn = _import_helper()
    executor = build_fn(web_research_enabled=False)
    assert executor._web_researcher is None
    assert executor._router._web_research_policy is None


def test_build_enabled_injects_web_research_classes():
    _, build_fn = _import_helper()
    executor = build_fn(web_research_enabled=True)
    from agents.web_research_policy import WebResearchPolicy
    from tools.web_research import WebResearcher
    assert isinstance(executor._web_researcher, WebResearcher)
    assert isinstance(executor._router._web_research_policy, WebResearchPolicy)


def test_build_disabled_no_import_side_effect():
    import sys
    before_policy = "agents.web_research_policy" in sys.modules
    before_researcher = "tools.web_research" in sys.modules
    _, build_fn = _import_helper()
    build_fn(web_research_enabled=False)
    after_policy = "agents.web_research_policy" in sys.modules
    after_researcher = "tools.web_research" in sys.modules
    # Should not have newly imported these modules
    assert after_policy == before_policy, "web_research_policy should not be imported when disabled"
    assert after_researcher == before_researcher, "web_research should not be imported when disabled"
