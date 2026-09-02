"""JARVIS persona SSOT sozlesmesi.

Bu dosya bir davranis kilididir. Uc seyi garanti eder:

1. **Tek kaynak.** Persona metni yalnizca `agents/persona.py` icinde tanimlanir;
   `config.py` de `agents/ollama_executor.py` de onu turetir. Repoda daha once
   birbirinden habersiz UC ayri persona tanimi vardi ve hangisinin konustugu
   JARVIS'in hangi kapidan baslatildigina bagliydi.
2. **Bozuk kodlama geri gelemez.** Canli L1 prompt'u modele
   `"Turkce kon??, gerekmedikce Ingilizce karis tirma."` gonderiyordu. Bu
   testler o bozulmayi (ve `world/*.json` icindekileri) yeniden uretmeyi
   basarisiz kilar.
3. **Sadakat protokolu kural seviyesinde.** Onceki personalarin hicbirinde acik
   bir sadakat/oncelik maddesi yoktu.

Bkz. FAILURES.md -> "Persona parcalanmasi" ve CLAUDE.md 5 (byte-safe patch).
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

# Bozuk-kodlama dedektoru artik `agents/data_classifier` icinde, `_fold_tr`
# ve `keyword_present` ile ayni evde tek kaynak olarak yasiyor. Kalite
# regresyon takimi (`eval/`) da ayni olcumu kullaniyor; iki kopya tutmak
# yerine buradan yeniden disa aktarilir.
from agents.data_classifier import corrupted_fragments  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. Modul var, yan etkisiz ve tek kaynak
# --------------------------------------------------------------------------- #

def test_persona_module_importable():
    from agents import persona

    assert hasattr(persona, "build_system_prompt")


def test_persona_module_is_side_effect_free():
    """Persona modulu saf olmali: import ederken hicbir sey yapmamali.

    config.py import aninda load_dotenv() cagirir ve HF_*_OFFLINE ortam
    degiskenlerini yazar; bu yuzden agents/ katmani config.py'yi import edemez
    (CLAUDE.md 9 -- .env'e dokunulmaz). Persona modulu her iki tarafin da
    guvenle turetebilmesi icin bagimliliksiz kalmali.

    Metin taramasi yerine AST kullaniliyor: aciklama satirlari yanlis pozitif
    uretmesin, ama gercek bir cagri/atama kacmasin.
    """
    tree = ast.parse((_REPO / "agents" / "persona.py").read_text(encoding="utf-8"))

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert imported <= {"__future__"}, (
        f"persona modulu bagimliliksiz olmali, su modulleri import ediyor: "
        f"{sorted(imported - {'__future__'})}"
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            assert name != "load_dotenv", "persona modulu .env okumamali"
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assert not isinstance(target, ast.Subscript), (
                    "persona modulu modul duzeyinde abonelik atamasi yapmamali "
                    "(os.environ[...] = ... gibi)"
                )


def test_ollama_executor_has_no_inline_persona():
    """Bozuk _SYSTEM_PROMPTS sozlugu geri gelmemeli."""
    src = (_REPO / "agents" / "ollama_executor.py").read_text(encoding="utf-8")
    assert "Sen JARVIS'sin. Ahmet Firat Cakmak" not in src, (
        "ollama_executor icinde satir-ici persona tanimi yeniden dogmus"
    )
    assert "from agents.persona import" in src or "from .persona import" in src, (
        "ollama_executor personayi SSOT modulunden turetmeli"
    )


def test_config_derives_system_prompt_from_persona():
    src = (_REPO / "config.py").read_text(encoding="utf-8")
    assert "persona" in src, "config.py personayi SSOT modulunden turetmeli"


# --------------------------------------------------------------------------- #
# 2. Karakter: uslup, hitap, sadakat
# --------------------------------------------------------------------------- #

def test_persona_addresses_user_as_efendim():
    from agents.persona import build_system_prompt

    assert "Efendim" in build_system_prompt()


def test_persona_declares_loyalty_protocol():
    """Mutlak sadakat kural seviyesinde yazili olmali."""
    from agents.persona import build_system_prompt

    text = build_system_prompt()
    assert "SADAKAT" in text.upper(), "sadakat protokolu basligi yok"
    assert "Ahmet" in text, "sadakatin kime oldugu yazili degil"


def test_persona_forbids_ai_boilerplate_and_moralising():
    from agents.persona import build_system_prompt

    text = build_system_prompt().lower()
    assert "gevezelik" in text, "gevezelik yasagi yok"
    assert "ahlak dersi" in text, "istenmeden ahlak dersi verme yasagi yok"


def test_persona_declares_grounding_rule():
    """Uydurma yasagi her seviyede olmali.

    Canli test sirasinda qwen2.5:7b, "Nerede kaldik?" sorusuna persona'daki
    ORNEK cumleyi gercek bir ani gibi aktardi -- yani prompt'un kendi ornekleri
    halusinasyon malzemesi oldu. Zemin blogu bunu yasaklar.
    Bkz. CLAUDE.md 8 (PUSULA): "uydurma degil, canli".
    """
    from agents.persona import build_system_prompt

    text = build_system_prompt()
    assert "uydurmazsın" in text or "uydurma" in text, "uydurma yasagi yok"
    assert "erişimim yok" in text, "erisim yoksa ne denecegi yazili degil"


def test_persona_marks_examples_as_style_only():
    """Ornek cumleler 'anı' degil 'uslup' olarak isaretlenmis olmali."""
    from agents.persona import build_system_prompt

    text = build_system_prompt()
    assert "ÜSLUP örnekleridir" in text, (
        "ornek cumleler uslup ornegi olarak isaretlenmemis -- zayif model "
        "bunlari gercek ani sanip aktarabilir"
    )


@pytest.mark.parametrize("level", ["L1", "L2", "L3"])
def test_every_level_carries_grounding_rule(level):
    from agents.persona import build_system_prompt

    assert "uydurma" in build_system_prompt(level=level)


def test_persona_keeps_pushback_rule():
    """Sadakat evet-adamlik degil: itiraz hakki korunmali."""
    from agents.persona import build_system_prompt

    text = build_system_prompt()
    assert "Evet-adam" in text or "evet-adam" in text


# --------------------------------------------------------------------------- #
# 3. Butun seviyeler personayi tasir, ama birbirinden ayirt edilebilir kalir
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("level", ["L1", "L2", "L3"])
def test_every_level_carries_persona_identity(level):
    from agents.persona import build_system_prompt

    text = build_system_prompt(level=level)
    assert "Efendim" in text, f"{level} hitabi kaybetmis"
    assert "SADAKAT" in text.upper(), f"{level} sadakat protokolunu kaybetmis"


def test_levels_remain_distinct():
    """Mevcut sozlesme (tests/test_ollama_system_prompt.py) korunur."""
    from agents.persona import build_system_prompt

    prompts = {lv: build_system_prompt(level=lv) for lv in ("L1", "L2", "L3")}
    assert len(set(prompts.values())) == 3, "seviyeler ayirt edilemez hale gelmis"


def test_voice_mode_is_off_by_default():
    from agents.persona import build_system_prompt

    assert "BU TUR SESLİ" not in build_system_prompt()
    assert "BU TUR SESLİ" not in build_system_prompt(level="L2")


@pytest.mark.parametrize("level", [None, "L1", "L2", "L3"])
def test_voice_mode_adds_spoken_instructions(level):
    """Model ses modunda oldugunu UNUTMAMALI.

    Sesli cevap hoparlorden okunur: markdown, kod ve uzun rapor sesli
    dinlenmez. Bu blok her seviyede eklenebilmeli.
    """
    from agents.persona import build_system_prompt

    metin = build_system_prompt(level=level, voice_mode=True)
    assert "BU TUR SESLİ" in metin
    assert "Markdown kullanma" in metin
    assert "Kod verme" in metin


def test_voice_block_comes_last():
    """Ses kurali seviye yonergesinden SONRA gelmeli.

    L2/L3 'calisabilir kod ver' diyor; ses modu 'kod okuma' diyor. Sonra
    gelen kazanir, yoksa model sesli olarak kod okumaya calisir.
    """
    from agents.persona import build_system_prompt

    metin = build_system_prompt(level="L2", voice_mode=True)
    assert metin.index("BU TUR SESLİ") > metin.index("BU TUR: TEKNİK")


def test_voice_mode_keeps_identity_and_loyalty():
    from agents.persona import build_system_prompt

    metin = build_system_prompt(level="L1", voice_mode=True)
    assert "Efendim" in metin
    assert "SADAKAT" in metin.upper()
    assert "uydurma" in metin


def test_name_is_injected():
    from agents.persona import build_system_prompt

    assert "Vizyon" in build_system_prompt(name="Vizyon")


# --------------------------------------------------------------------------- #
# 4. Bozuk kodlama regresyon kilidi
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("level", [None, "L1", "L2", "L3"])
def test_persona_text_has_no_corrupted_turkish(level):
    from agents.persona import build_system_prompt

    bad = corrupted_fragments(build_system_prompt(level=level))
    assert not bad, f"persona metninde bozuk kodlama: {bad}"


@pytest.mark.parametrize("rel", [
    "agents/persona.py",
    "agents/ollama_executor.py",
    "world/people.json",
    "world/devices.json",
    "world/rooms.json",
    "world/projects.json",
    "world/modes.json",
    "world/home.json",
])
def test_live_files_have_no_corrupted_turkish(rel):
    path = _REPO / rel
    assert path.exists(), f"{rel} bulunamadi"
    bad = corrupted_fragments(path.read_text(encoding="utf-8"))
    assert not bad, f"{rel} icinde bozuk kodlama: {bad}"


@pytest.mark.parametrize("rel", ["world/people.json", "world/devices.json"])
def test_world_files_still_parse_as_json(rel):
    """Kodlama duzeltmesi dosyayi bozmamali."""
    data = json.loads((_REPO / rel).read_text(encoding="utf-8"))
    assert data.get("schema_version") == 1


def test_detector_actually_detects():
    """Dedektorun kendisi calisiyor mu? (yanlis-negatif korumasi)"""
    assert corrupted_fragments("Turkce kon??, gerekmedikce Ingilizce karis tirma.")
    assert corrupted_fragments("Jarvis ilerlemesinde g?sterilebilir demo")
    assert not corrupted_fragments("Türkçe konuş, gerekmedikçe İngilizce karıştırma.")
    assert not corrupted_fragments('url="/login?blocked=1"')
