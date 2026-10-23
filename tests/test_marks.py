"""has_unlikely_marks() and has_hidden_overlay() beyond the conformance fixtures."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from confusable import has_hidden_overlay, has_unlikely_marks
from confusable._marks import has_repeated_mark
from confusable._normalize import nfc, nfd


@pytest.mark.parametrize(
    ("text", "unlikely"),
    [
        ("", False),
        ("abc", False),
        ("e\u0301\u0301", True),  # the same mark twice
        ("e\u0301\u0300\u0301", True),  # twice, with another between
        ("a\u20dd\u20dd", True),  # an enclosing mark (Me) twice
        ("a\u0301b\u0301", False),  # the same mark on two bases
        ("a\u0300\u0301\u0302\u0303", False),  # four marks
        ("a\u0300\u0301\u0302\u0303\u0304", True),  # five
        # LATIN SMALL LETTER E WITH CIRCUMFLEX AND DOT BELOW brings two marks.
        ("\u1ec7\u0300\u0301\u0303", True),
        # A spacing mark (Mc), DEVANAGARI VOWEL SIGN AA, ends a run.
        ("\u0915\u0941\u093e\u0941", False),
    ],
)
def test_unlikely_marks(text: str, unlikely: bool) -> None:
    assert has_unlikely_marks(text) is unlikely


def test_too_many_marks_is_not_icus_invisible_check() -> None:
    five = "a\u0300\u0301\u0302\u0303\u0304"
    assert has_unlikely_marks(five)
    assert not has_repeated_mark(five)


@pytest.mark.parametrize(
    ("text", "hidden"),
    [
        ("", False),
        ("i", False),
        ("\u0307", False),  # no base character
        ("a\u0307", False),
        ("i\u0307", True),
        ("j\u0307", True),
        ("l\u0307", True),
        ("\u0131\u0307", True),  # LATIN SMALL LETTER DOTLESS I
        ("\u0237\u0307", True),  # LATIN SMALL LETTER DOTLESS J
        ("\u0456\u0307", True),  # Soft_Dotted CYRILLIC SMALL LETTER ...I
        ("I\u0307", True),  # prototype l
        ("1\u0307", True),  # prototype l
        ("i\u0323\u0307", True),  # a mark below does not separate them
        ("i\u0301\u0307", False),  # a mark above does
        ("\u1e37\u0307", True),  # NFD: l, dot below, dot above
    ],
)
def test_hidden_overlay(text: str, hidden: bool) -> None:
    assert has_hidden_overlay(text) is hidden


def test_capital_i_with_dot_above_is_a_hidden_overlay() -> None:
    # A deliberate difference from ICU, which tests the text as written and so
    # only flags the decomposed form. Turkish text with U+0130 is flagged.
    assert has_hidden_overlay("\u0130")
    assert has_hidden_overlay("I\u0307")
    assert has_hidden_overlay("\u0130stanbul")


marked_text = st.text(
    st.sampled_from(
        "aeijlI1\u0131\u0130\u1e37\u1ec7\u00e9"
        "\u0300\u0301\u0302\u0307\u0323\u0328\u20dd\u093e"
    ),
    max_size=12,
)


@given(marked_text)
def test_checks_ignore_normalization(text: str) -> None:
    for check in (has_unlikely_marks, has_hidden_overlay):
        assert check(text) == check(nfd(text)) == check(nfc(text))
