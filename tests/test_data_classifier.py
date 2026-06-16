"""Tests for the Data Classifier (FAZ 1B.13E)."""
import pytest

from agents.data_classifier import classify
from agents.provider_profiles import DATA_CLASS_SET


# --------------------------------------------------------------------------
# Default behaviour: public unless a concrete signal is found
# --------------------------------------------------------------------------


def test_generic_question_defaults_to_public():
    assert classify("Python'da liste nasil ters cevrilir?") == "public"


def test_empty_text_defaults_to_public():
    assert classify("") == "public"


def test_none_text_defaults_to_public():
    assert classify(None) == "public"


def test_whitespace_only_text_defaults_to_public():
    assert classify("    ") == "public"


# --------------------------------------------------------------------------
# institution_internal signals
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "ESHOT rolanti raporunu kontrol eder misin?",
        "BYS sisteminden veri cekebilir misin?",
        "Bium uzerinden indirme yapalim mi?",
        "Bugunku surucu karnesi verisini ozetler misin?",
    ],
)
def test_workplace_signal_triggers_institution_internal(text):
    assert classify(text) == "institution_internal"


def test_workplace_signal_matches_without_turkish_diacritics():
    # "şirket içi" typed without diacritics: "sirket ici"
    assert classify("Bu sirket ici bir rapor, dikkatli ol.") == "institution_internal"


# --------------------------------------------------------------------------
# sensitive signals (legal / financial)
# --------------------------------------------------------------------------


def test_legal_signal_triggers_sensitive():
    assert classify("Dilara'nin yarinki dava dosyasini kontrol eder misin?") == "sensitive"


def test_financial_signal_triggers_sensitive():
    assert classify("IBAN numaramla odeme yapar misin?") == "sensitive"


@pytest.mark.parametrize(
    "text",
    [
        "Avukatla gorusmeyi planla.",
        "Muvekkil dosyasini incele.",
        "Kredi karti ekstresine bak.",
        "Kripto cuzdan bakiyemi kontrol et.",
    ],
)
def test_more_sensitive_signals(text):
    assert classify(text) == "sensitive"


# --------------------------------------------------------------------------
# personal signals
# --------------------------------------------------------------------------


def test_tc_kimlik_phrase_triggers_personal():
    assert classify("TC kimlik numaramı not aldın mı?") == "personal"


def test_bare_eleven_digit_number_triggers_personal():
    assert classify("12345678901 numarali hesaba bakar misin?") == "personal"


def test_ten_digit_number_does_not_trigger_personal():
    # one digit short of the TC-kimlik/phone-length heuristic
    assert classify("1234567890 numarali siparisi kontrol et.") == "public"


def test_twelve_digit_number_does_not_trigger_personal():
    # one digit over -- must not match via substring leakage either
    assert classify("123456789012 takip numarali kargo.") == "public"


# --------------------------------------------------------------------------
# Precedence: most restrictive matching category wins
# --------------------------------------------------------------------------


def test_institution_internal_takes_precedence_over_sensitive():
    # contains both an ESHOT signal and a legal signal
    assert classify("ESHOT'taki dava dosyasini bulabilir misin?") == "institution_internal"


def test_sensitive_takes_precedence_over_personal():
    # contains both a financial signal and a bare 11-digit number
    assert classify("IBAN: 12345678901 numarali hesaba odeme yap.") == "sensitive"


# --------------------------------------------------------------------------
# Scope lock: this classifier may NEVER produce redacted/synthetic, and
# must always stay within DATA_CLASS_SET
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Merhaba",
        "Python kodu yaz",
        "ESHOT raporu",
        "Dava dosyasi",
        "TC kimlik numaram 12345678901",
        "",
        None,
        "Bugun hava nasil?",
        "12345678901",
    ],
)
def test_classifier_never_returns_redacted_or_synthetic(text):
    result = classify(text)
    assert result in DATA_CLASS_SET
    assert result not in {"redacted", "synthetic"}
