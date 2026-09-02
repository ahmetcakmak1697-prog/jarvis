"""main.py'nin fiilen kullandigi ajanin dogru katmanlara bagli oldugunu kilitler.

`python main.py` -> `agent/local_agent.py` -> `LocalJarvisAgent`. Bu yol
kaskada (`AssistantExecutor` -> `OllamaExecutor`) hic ugramaz. Sonuc olarak iki
duzeltme bu dosyayi atladi:

1. **Model secimi.** `runtime_profiles.json` aktif profilde
   `local_small=qwen2.5:7b`, `local_main=mistral-nemo:latest` diyor; ama
   `local_agent.py` kendi `MODELS` sozlugunde `llama3.1` yaziyordu. Canli
   calistirmada terminal `-> llama3.1` gosterdi: profilde bulunmayan bir model.
   CLAUDE.md 7: "Model adi koda gomulmez -> ModelRegistry."

2. **Persona.** SSOT birlestirmesi (`agents/persona.py`) repodaki UC persona
   tanimini topladi; bu DORDUNCUSUYDU ve kacirildi. Icindeki ornek cumle
   ("Anliyorum efendim, Pazartesi'siniz.") canli testte modele aynen tekrar
   ettirildi -- `tests/test_persona_ssot.py::test_persona_marks_examples_as_style_only`
   tam bu sinifi engellemek icin yazilmisti ama bu dosyayi kapsamiyordu.

Bkz. `tests/test_persona_ssot.py` (persona SSOT sozlesmesi) ve FAILURES.md.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_LOCAL_AGENT = _REPO / "agent" / "local_agent.py"

#: Ollama model adi deseni: aile adi, istege bagli ":etiket".
#: Yorum satirlari taranmaz -- yalnizca gercek string sabitleri (AST).
_MODEL_NAME = re.compile(
    r"\b(llama|qwen|mistral|mixtral|gemma|phi|deepseek|nemo)[\w.\-]*(:[\w.\-]+)?",
    re.IGNORECASE,
)


def _string_constants(path: Path) -> list[str]:
    """Dosyadaki tum string sabitlerini dondurur (docstring'ler dahil degil).

    Metin taramasi yerine AST: aciklama satirindaki "llama3.1 kullaniyorduk"
    gibi tarihsel notlar yanlis pozitif uretmesin, ama gercek bir sabit kacmasin.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                docstrings.add(id(first.value))

    return [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


# --------------------------------------------------------------------------- #
# 1. Model adlari koda gomulmez
# --------------------------------------------------------------------------- #

def test_local_agent_does_not_hardcode_model_names():
    """CLAUDE.md 7: model adi koda gomulmez, ModelRegistry rolu istenir."""
    found = [s for s in _string_constants(_LOCAL_AGENT) if _MODEL_NAME.search(s)]
    assert not found, (
        f"local_agent.py icinde gomulu model adi var: {found}. "
        f"ModelRegistry rollerini kullan (local_small / local_main)."
    )


def test_local_agent_uses_model_registry():
    src = _LOCAL_AGENT.read_text(encoding="utf-8")
    assert "ModelRegistry" in src, (
        "local_agent model adlarini ModelRegistry uzerinden cozmeli"
    )


def test_local_agent_model_roles_come_from_active_profile():
    """Secilen modeller gercekten aktif profilde tanimli olmali.

    llama3.1 profilde hic gecmiyordu; yine de canli calisan modeldi. Bu test
    kod ile `config/runtime_profiles.json` arasindaki baglantiyi kilitler.
    """
    from agents.model_registry import ModelRegistry

    reg = ModelRegistry()
    assert reg.local_small(), "local_small rolu bos"
    assert reg.local_main(), "local_main rolu bos"


# --------------------------------------------------------------------------- #
# 2. Persona SSOT'tan turer
# --------------------------------------------------------------------------- #

def test_local_agent_has_no_inline_persona():
    """Dorduncu persona tanimi geri gelmemeli."""
    src = _LOCAL_AGENT.read_text(encoding="utf-8")
    assert "Sen JARVIS — kullanıcının en güvendiği" not in src, (
        "local_agent icinde satir-ici persona tanimi yeniden dogmus"
    )


def test_local_agent_derives_persona_from_ssot():
    src = _LOCAL_AGENT.read_text(encoding="utf-8")
    assert "from agents.persona import" in src, (
        "local_agent personayi agents/persona.py'den turetmeli"
    )
    assert "build_system_prompt" in src, (
        "local_agent build_system_prompt() kullanmali"
    )


def test_local_agent_does_not_ship_parrotable_example():
    """Zayif model prompt'taki ornegi ani sanip aynen tekrar ediyordu.

    Canli kanit: "Anliyorum efendim, Pazartesi'siniz." cumlesi prompt'ta ornek
    olarak duruyordu ve model onu kullaniciya cevap olarak verdi.
    """
    src = _LOCAL_AGENT.read_text(encoding="utf-8")
    assert "Pazartesi'siniz" not in src, (
        "papagan edilebilir ornek cumle hala prompt'ta"
    )
