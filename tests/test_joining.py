"""Joining controls in the limited contexts of UTS #39 section 3.1.1.1."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from confusable import is_allowed, restriction_level
from confusable._data.joining import JOINING_TYPE_RUNS
from confusable._data.normalization import CANONICAL_COMBINING_CLASS
from confusable._joining import joining_controls_in_context
from confusable._lookup import Runs
from confusable._normalize import nfc, nfd

ZWNJ = "\u200c"
ZWJ = "\u200d"

# The three figures of UTS #39 section 3.1.1.1.
PERSIAN = "\u0646\u0627\u0645\u0647" + ZWNJ + "\u0627\u06cc"  # A1
MALAYALAM = (  # A2: eyewitness
    "\u0d26\u0d43\u0d15\u0d4d" + ZWNJ + "\u0d38\u0d3e\u0d15\u0d4d\u0d37\u0d3f"
)
SINHALA = "\u0dc1\u0dca" + ZWJ + "\u0dbb\u0dd3"  # B: Sri


@pytest.mark.parametrize("word", [PERSIAN, MALAYALAM, SINHALA])
def test_figures_of_the_specification(word: str) -> None:
    assert joining_controls_in_context(word) == [True]
    assert not is_allowed(word)
    assert is_allowed(word, joining_controls=True)
    assert is_allowed(word.replace(ZWNJ, "").replace(ZWJ, ""))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", []),
        ("abc", []),
        ("a" + ZWNJ + "b", [False]),  # Latin does not join
        ("a" + ZWJ + "b", [False]),
        (ZWNJ, [False]),
        (ZWJ, [False]),
        # A1 needs a left-joining character before: ALEF only joins right.
        ("\u0627" + ZWNJ + "\u0628", [False]),
        ("\u0628" + ZWNJ + "\u0627", [True]),  # BEH then ALEF
        ("\u0628\u064e" + ZWNJ + "\u0627", [True]),  # a transparent FATHA between
        ("\u0628" + ZWNJ + "\u064e\u0627", [False]),  # but not after the ZWNJ
        ("\u0628" + ZWNJ, [False]),  # nothing to join to
        ("\u0628" + ZWNJ + "\u0710", [False]),  # BEH and SYRIAC ALAPH: two scripts
        # A2 and B need a letter, then a virama, then the joining control.
        ("\u0915\u094d" + ZWNJ + "\u0937", [True]),  # Devanagari KA, VIRAMA, SSA
        ("\u0915" + ZWNJ + "\u0937", [False]),  # no virama
        ("\u094d" + ZWNJ + "\u0937", [False]),  # no letter
        ("\u0915\u094d" + ZWNJ, [False]),  # A2 needs a letter after
        ("\u0915\u094d" + ZWJ, [True]),  # B does not
        ("\u0915\u094d" + ZWJ + "\u0937", [True]),
        ("\u0915\u094d" + ZWJ + "\u093e", [False]),  # a dependent vowel after
        ("a\u094d" + ZWJ, [False]),  # Latin a with a Devanagari virama
        # Marks with a nonzero combining class may sit around the virama.
        ("\u0915\u093c\u094d" + ZWNJ + "\u0937", [True]),  # NUKTA before
        ("\u0d15\u0d4d\u0951" + ZWNJ + "\u0d38", [True]),  # UDATTA after
        ("\u0d15\u0d4d" + ZWNJ + "\u0951\u0d38", [True]),
        # U+0301's Script_Extensions leave out Malayalam: two scripts.
        ("\u0d15\u0d4d\u0301" + ZWNJ + "\u0d38", [False]),
        # A spacing mark is not one of them: MALAYALAM VOWEL SIGN AA.
        ("\u0d15\u0d4d\u0d3e" + ZWNJ + "\u0d38", [False]),
        # Each joining control is judged on its own.
        (PERSIAN + "a" + ZWNJ + "b" + SINHALA, [True, False, True]),
    ],
)
def test_contexts(text: str, expected: list[bool]) -> None:
    assert joining_controls_in_context(text) == expected


def test_one_joining_control_out_of_context_fails_the_text() -> None:
    assert not is_allowed(PERSIAN + ZWNJ, joining_controls=True)
    assert not is_allowed("a" + ZWJ + "b", joining_controls=True)


def test_restriction_level_passes_the_option_on() -> None:
    assert restriction_level(SINHALA).name == "UNRESTRICTED"
    assert restriction_level(SINHALA, joining_controls=True).name == "SINGLE_SCRIPT"


joining_text = st.text(
    st.sampled_from(
        "ab\u0627\u0628\u0647\u064e\u0710\u0915\u0928\u0929\u093c\u093e\u094d"
        "\u0d15\u0d38\u0d3e\u0d4d\u0301\u0323\u0951" + ZWNJ + ZWJ
    ),
    max_size=10,
)


@given(joining_text)
def test_contexts_ignore_normalization(text: str) -> None:
    expected = joining_controls_in_context(text)
    assert joining_controls_in_context(nfd(text)) == expected
    assert joining_controls_in_context(nfc(text)) == expected
    allowed = is_allowed(text, joining_controls=True)
    assert is_allowed(nfd(text), joining_controls=True) == allowed
    assert is_allowed(nfc(text), joining_controls=True) == allowed


JOINING_TYPE = Runs(JOINING_TYPE_RUNS)


def _contextj(text: str, i: int) -> bool:
    """IDNA2008's CONTEXTJ rule (RFC 5892 appendix A) for the joiner at i."""
    if i > 0 and CANONICAL_COMBINING_CLASS.get(ord(text[i - 1])) == 9:
        return True
    if text[i] == ZWJ:
        return False
    before, after = i - 1, i + 1
    while before >= 0 and JOINING_TYPE[ord(text[before])] == "T":
        before -= 1
    while after < len(text) and JOINING_TYPE[ord(text[after])] == "T":
        after += 1
    return (
        before >= 0
        and after < len(text)
        and JOINING_TYPE[ord(text[before])] in ("L", "D")
        and JOINING_TYPE[ord(text[after])] in ("R", "D")
    )


@given(joining_text)
def test_contexts_are_narrower_than_idna(text: str) -> None:
    # UTS #39 says any text that meets A1, A2 and B also meets CONTEXTJ. That
    # holds except where a mark sits between the virama and the joining
    # control, which A2 and B allow and CONTEXTJ does not.
    composed = nfc(text)
    joiners = [i for i, c in enumerate(composed) if c in (ZWNJ, ZWJ)]
    for i, ok in zip(joiners, joining_controls_in_context(text), strict=True):
        if ok and CANONICAL_COMBINING_CLASS.get(ord(composed[i - 1]), 0) in (0, 9):
            assert _contextj(composed, i)
