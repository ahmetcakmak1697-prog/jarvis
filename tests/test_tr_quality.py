"""Turkish character quality tests - FAZ-T1-S1.

Deterministic regression guards for _fold_tr and Turkish encoding correctness.
No subjective judgment. No network. No model calls.
"""

from agents.assistant_executor import _fold_tr as _fold_tr_executor
from agents.data_classifier import _fold_tr as _fold_tr_classifier


# -- Python gotcha guard -------------------------------------------------------

def test_python_dotted_capital_i_lower_produces_combining_dot():
    """Confirm the Python gotcha: 'İ'.lower() gives TWO codepoints, not 'i'.

    This is the root cause of the _fold_tr requirement. Guard against Python
    version changes that might silently 'fix' this and break our assumptions.
    """
    lowered = "İ".lower()
    # Python maps U+0130 → 'i' + U+0307 (COMBINING DOT ABOVE)
    assert len(lowered) == 2, f"expected 2 codepoints, got {len(lowered)}: {[hex(ord(c)) for c in lowered]}"
    assert lowered[0] == "i"
    assert ord(lowered[1]) == 0x0307  # COMBINING DOT ABOVE


def test_fold_tr_avoids_combining_dot_gotcha():
    """_fold_tr must map İ to plain 'i', not 'i' + COMBINING DOT ABOVE."""
    result = _fold_tr_executor("İ")
    assert result == "i", f"expected 'i', got {result!r} (codepoints: {[hex(ord(c)) for c in result]})"
    assert len(result) == 1


# -- Round-trip: all 7 Turkish characters -------------------------------------

_TR_CASES = [
    ("İ", "i"),   # İ — capital dotted I
    ("ı", "i"),   # ı — dotless I
    ("ğ", "g"),   # ğ — soft G
    ("ş", "s"),   # ş — S-cedilla
    ("ç", "c"),   # ç — C-cedilla
    ("ö", "o"),   # ö — O-umlaut
    ("ü", "u"),   # ü — U-umlaut
]


def test_fold_tr_executor_all_turkish_chars():
    for char, expected in _TR_CASES:
        result = _fold_tr_executor(char)
        assert result == expected, f"executor: {char!r} ({hex(ord(char))}) → {result!r}, expected {expected!r}"


def test_fold_tr_classifier_all_turkish_chars():
    for char, expected in _TR_CASES:
        result = _fold_tr_classifier(char)
        assert result == expected, f"classifier: {char!r} ({hex(ord(char))}) → {result!r}, expected {expected!r}"


# -- Consistency: both implementations must agree ------------------------------

_CONSISTENCY_STRINGS = [
    "İyi",              # İyi
    "İstanbul",         # İstanbul
    "şehir",            # şehir
    "Güneş",       # Güneş
    "ğüçlü", # güçlü
    "ışık",   # ışık
    "çalışma", # çalışma
]


def test_both_fold_tr_implementations_are_consistent():
    for s in _CONSISTENCY_STRINGS:
        r1 = _fold_tr_executor(s)
        r2 = _fold_tr_classifier(s)
        assert r1 == r2, f"divergence on {s!r}: executor={r1!r}, classifier={r2!r}"


# -- No codepoint loss: non-empty Turkish input must not produce empty output --

def test_fold_tr_does_not_produce_empty_for_turkish_input():
    for char, _ in _TR_CASES:
        assert _fold_tr_executor(char) != ""
        assert _fold_tr_classifier(char) != ""


# -- Mojibake guard: no U+FFFD replacement characters in known fold outputs ---

_MOJIBAKE_INPUTS = [
    "İSTANBUL",          # İSTANBUL
    "şEHİR",        # şEHİR
    "GÜNEŞ",        # GÜNEŞ (uppercase)
    "ışık",    # ışık
]


def test_fold_tr_outputs_contain_no_replacement_chars():
    for s in _MOJIBAKE_INPUTS:
        result_e = _fold_tr_executor(s)
        result_c = _fold_tr_classifier(s)
        assert "�" not in result_e, f"executor replacement char in {s!r} → {result_e!r}"
        assert "�" not in result_c, f"classifier replacement char in {s!r} → {result_c!r}"


# -- Mixed-case known outputs -------------------------------------------------

def test_fold_tr_istanbul_uppercase():
    assert _fold_tr_executor("İSTANBUL") == "istanbul"
    assert _fold_tr_classifier("İSTANBUL") == "istanbul"


def test_fold_tr_sehir_mixed():
    # şEHİR → sehir
    assert _fold_tr_executor("şEHİR") == "sehir"
    assert _fold_tr_classifier("şEHİR") == "sehir"


def test_fold_tr_gunes_uppercase():
    # GÜNEŞ → gunes
    assert _fold_tr_executor("GÜNEŞ") == "gunes"
    assert _fold_tr_classifier("GÜNEŞ") == "gunes"


# -- Edge cases ---------------------------------------------------------------

def test_fold_tr_empty_string():
    assert _fold_tr_executor("") == ""
    assert _fold_tr_classifier("") == ""


def test_fold_tr_none_input():
    assert _fold_tr_executor(None) == ""
    assert _fold_tr_classifier(None) == ""


def test_fold_tr_ascii_only_unchanged_case():
    # Plain ASCII lowercase should be unaffected
    assert _fold_tr_executor("jarvis") == "jarvis"
    assert _fold_tr_classifier("jarvis") == "jarvis"
