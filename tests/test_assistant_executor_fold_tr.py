from __future__ import annotations
from agents.assistant_executor import _fold_tr, _QUICK_REPLIES

def test_fold_tr_handles_real_turkish_dotted_capital_i():
    s = "\u0130yi"
    assert ord(s[0]) == 0x130
    assert _fold_tr(s) == "iyi"

def test_dotted_capital_i_quick_reply_matches():
    s = "\u0130yi"
    folded = _fold_tr(s).strip(" .!?")
    assert folded in _QUICK_REPLIES
    assert _QUICK_REPLIES[folded] == "Tamamdir."

def test_dotted_capital_i_in_longer_quick_reply_word():
    s = "\u0130yi"
    assert _fold_tr(s) == _fold_tr("iyi")

def test_plain_ascii_i_still_works_unchanged():
    assert _fold_tr("IYI") == "iyi"

def test_fold_tr_still_handles_other_turkish_chars():
    assert _fold_tr("I\u011e\u00dc\u015e\u00d6\u00c7") == "igusoc"
