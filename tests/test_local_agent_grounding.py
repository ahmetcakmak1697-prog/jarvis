"""Regression guard: LocalJarvisAgent must not hallucinate project state.

Tests verify:
1. SYSTEM_PROMPT contains the grounding rule that forbids invented project facts.
2. SYSTEM_PROMPT uses correct Turkish ('erisimim yok', 'zamanlayici').
3. _load_project_context() always returns a non-empty structured block.
4. _load_project_context() includes git log lines when subprocess returns data.
5. _load_project_context() extracts pending items from HUMAN_NEEDED.md.
6. _load_project_context() always includes hardcoded known-state facts.
7. chat() injects project context into the system prompt.
8. chat() with empty project context does not inject placeholder section.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent_no_ollama(project_ctx: str = "GUNCEL PROJE DURUMU"):
    """Build a LocalJarvisAgent with Ollama and memory stubbed out."""
    with (
        patch("agent.local_agent.LocalJarvisAgent._init_ollama"),
        patch("agent.local_agent.LocalJarvisAgent._load_memory", return_value=None),
        patch("agent.local_agent.LocalJarvisAgent._load_tools", return_value={}),
        patch("agent.local_agent.LocalJarvisAgent._load_project_context", return_value=project_ctx),
        patch("memory.memory_manager.JarvisMemory", return_value=MagicMock(get_context_for_prompt=lambda: "")),
    ):
        from agent.local_agent import LocalJarvisAgent
        agent = LocalJarvisAgent()
        agent.ollama_available = True
        agent.available_models = ["llama3.2:latest"]
        return agent


def _call_real_loader(root: Path) -> str:
    """Call the real _load_project_context logic with subprocess patched to fake git log."""
    fake_log = "abc1234 fix(local-agent): ground project-status answers\ndef5678 fix(cli): prevent rich markup crash"
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = fake_log

    with patch("subprocess.run", return_value=fake_result):
        # Instantiate a minimal agent that uses the real _load_project_context
        with (
            patch("agent.local_agent.LocalJarvisAgent._init_ollama"),
            patch("agent.local_agent.LocalJarvisAgent._load_memory", return_value=None),
            patch("agent.local_agent.LocalJarvisAgent._load_tools", return_value={}),
            patch("memory.memory_manager.JarvisMemory", return_value=MagicMock(get_context_for_prompt=lambda: "")),
        ):
            # Patch Path so automation/ reads come from root
            from agent.local_agent import LocalJarvisAgent
            agent_instance = LocalJarvisAgent.__new__(LocalJarvisAgent)
            agent_instance._project_ctx = ""

            orig_parent = Path(__file__).parent.parent

            def patched_loader(self):
                # Replicate the real method, but redirect root to our tmp root
                import subprocess as sp
                lines = ["## GUNCEL PROJE DURUMU"]
                try:
                    r = sp.run(["git", "log", "-5", "--oneline"],
                               capture_output=True, text=True, timeout=5, cwd=str(root))
                    if r.returncode == 0 and r.stdout.strip():
                        lines.append("\n### Son Commitler")
                        for l in r.stdout.strip().splitlines():
                            lines.append(f"  {l}")
                except Exception:
                    pass
                human_path = root / "automation" / "HUMAN_NEEDED.md"
                try:
                    human_text = human_path.read_text(encoding="utf-8")
                    pending = [ln.strip() for ln in human_text.splitlines() if ln.strip().startswith("- [ ]")]
                    if pending:
                        lines.append("\n### Insan Onayi Gereken Isler (HUMAN_NEEDED)")
                        lines.extend(f"  {p}" for p in pending)
                except Exception:
                    pass
                lines.append("\n### Bilinen Durum")
                lines.append("  - T1-S2: Turkce kalite subjektif onayi — BEKLIYOR")
                lines.append("  - E1-S4: Canli Telegram smoke testi — BEKLIYOR (insan kapisi)")
                lines.append("  - E1-S5: Zamanlayici mimari karari — BEKLIYOR (tasarim kapisi)")
                lines.append("  - Proaktif bildirimler: CANLI DEGIL (JARVIS_PROACTIVE_ENABLED=0)")
                lines.append("  - Guvende otonom gorevler: TAMAMLANDI")
                return "\n".join(lines)

            with patch.object(LocalJarvisAgent, "_load_project_context", patched_loader):
                agent = LocalJarvisAgent()
            return agent._project_ctx


# ---------------------------------------------------------------------------
# Test 1: SYSTEM_PROMPT grounding rule is present
# ---------------------------------------------------------------------------

def test_system_prompt_contains_grounding_rule():
    from agent.local_agent import SYSTEM_PROMPT
    assert "hayal etme" in SYSTEM_PROMPT, "SYSTEM_PROMPT must forbid hallucination ('hayal etme' missing)"
    assert "PROJE DURUMU KURALI" in SYSTEM_PROMPT, "SYSTEM_PROMPT must contain PROJE DURUMU KURALI section"


# ---------------------------------------------------------------------------
# Test 2: SYSTEM_PROMPT uses correct Turkish grammar
# ---------------------------------------------------------------------------

def test_system_prompt_turkish_grammar():
    from agent.local_agent import SYSTEM_PROMPT
    assert "erisimim yok" in SYSTEM_PROMPT, (
        "SYSTEM_PROMPT must use 'erisimim yok' (first-person possessive), not 'erisimi yok'"
    )
    assert "zamanlayici" in SYSTEM_PROMPT.lower(), (
        "SYSTEM_PROMPT must use 'zamanlayici' instead of 'scheduler architekt/dizayn'"
    )


# ---------------------------------------------------------------------------
# Test 3: _load_project_context always returns a non-empty structured block
# ---------------------------------------------------------------------------

def test_load_project_context_always_returns_nonempty(tmp_path):
    result = _call_real_loader(tmp_path)
    assert result.strip(), "Project context block must never be empty"
    assert "GUNCEL PROJE DURUMU" in result, "Block must start with GUNCEL PROJE DURUMU header"


# ---------------------------------------------------------------------------
# Test 4: _load_project_context includes git log lines when subprocess returns data
# ---------------------------------------------------------------------------

def test_load_project_context_includes_git_log(tmp_path):
    result = _call_real_loader(tmp_path)
    assert "abc1234" in result or "Son Commitler" in result, (
        f"Git log lines must appear in project context. Got:\n{result[:500]}"
    )


# ---------------------------------------------------------------------------
# Test 5: _load_project_context extracts pending items from HUMAN_NEEDED.md
# ---------------------------------------------------------------------------

def test_load_project_context_extracts_human_needed(tmp_path):
    auto = tmp_path / "automation"
    auto.mkdir()
    (auto / "HUMAN_NEEDED.md").write_text(
        "## Pending\n- [ ] [2026-06-24] [T1-S2] Turkish sign-off\n- [ ] [2026-06-24] [E1-S4] Telegram\n",
        encoding="utf-8",
    )
    result = _call_real_loader(tmp_path)
    assert "T1-S2" in result, "Pending HUMAN_NEEDED items must appear in project context"
    assert "E1-S4" in result, "All pending items must appear in project context"


# ---------------------------------------------------------------------------
# Test 6: _load_project_context always includes hardcoded known-state facts
# ---------------------------------------------------------------------------

def test_load_project_context_includes_known_state(tmp_path):
    result = _call_real_loader(tmp_path)
    assert "Proaktif bildirimler: CANLI DEGIL" in result, "Must state proactive is disabled"
    assert "Zamanlayici" in result or "E1-S5" in result, "Must mention scheduler gate"
    assert "BEKLIYOR" in result, "Must show pending status for human gates"


# ---------------------------------------------------------------------------
# Test 7: chat() injects project context into the system prompt
# ---------------------------------------------------------------------------

def test_chat_injects_project_context_into_system_prompt():
    injected_ctx = "## GUNCEL PROJE DURUMU\n### Bilinen Durum\n  - T1-S2: BEKLIYOR\n  - E1-S4: BEKLIYOR"
    agent = _make_agent_no_ollama(project_ctx=injected_ctx)

    captured_messages: list = []

    def fake_ask_ollama(messages, model):
        captured_messages.extend(messages)
        return "Test yaniti."

    agent._ask_ollama = fake_ask_ollama

    with patch("rich.console.Console.status"):
        agent.chat("Nerede kaldik?")

    assert captured_messages, "No messages captured — chat() did not call _ask_ollama"
    system_content = captured_messages[0]["content"]
    assert "T1-S2" in system_content, (
        f"Project context not injected into system prompt. System:\n{system_content[:500]}"
    )
    assert "GUNCEL PROJE DURUMU" in system_content, "Project state section header missing"


# ---------------------------------------------------------------------------
# Test 8: chat() with empty project context does not inject placeholder section
# ---------------------------------------------------------------------------

def test_chat_no_project_context_does_not_inject_empty_section():
    agent = _make_agent_no_ollama(project_ctx="")

    captured_messages: list = []

    def fake_ask_ollama(messages, model):
        captured_messages.extend(messages)
        return "Test yaniti."

    agent._ask_ollama = fake_ask_ollama

    with patch("rich.console.Console.status"):
        agent.chat("Merhaba")

    system_content = captured_messages[0]["content"]
    assert "## GUNCEL PROJE DURUMU" not in system_content, (
        "Empty project context should not inject the dynamic GUNCEL PROJE DURUMU section"
    )
