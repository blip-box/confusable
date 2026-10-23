"""The public skeleton() and match() beyond what the conformance fixtures pin."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import confusable
from confusable import Match, match, skeleton

LTR_STRONG = "abc"
RTL_STRONG = "\u05d0\u05d1"  # HEBREW LETTER ALEF, BET

# Letters of both directions, digits and neutrals; no paragraph separators
# or isolates, so the first strong character sets the paragraph direction.
bidi_text = st.text(st.sampled_from(f"{LTR_STRONG}{RTL_STRONG}12 ()!."))


@given(bidi_text)
def test_auto_direction_follows_the_first_strong_character(text: str) -> None:
    strong = [c for c in text if c in LTR_STRONG + RTL_STRONG]
    rtl = bool(strong) and strong[0] in RTL_STRONG
    assert skeleton(text, "auto") == skeleton(text, "rtl" if rtl else "ltr")


def test_rtl_mirrors_brackets() -> None:
    assert skeleton("(", "ltr") == "("
    assert skeleton("(", "rtl") == ")"


def test_direction_must_be_known() -> None:
    with pytest.raises(ValueError, match="direction"):
        skeleton("abc", "up")  # type: ignore[arg-type]


def test_lone_surrogates_do_not_crash() -> None:
    # Python strings can hold them (surrogateescape, for example).
    assert skeleton("a\udcff") == skeleton("a\udcff")
    assert match("a\udcff", "a\udcff")


def test_match_is_false_when_skeletons_differ() -> None:
    result = match("paypal", "paypa1x")
    assert not result
    assert result == Match(0)


def test_match_uses_the_display_direction() -> None:
    # UTS #39 section 4: LTR-confusable, but not confusable without bidi.
    s1, s2 = "A1<\u05e9\u05c2", "\u0391\u05e9\u05ba>1"
    assert match(s1, s2) == Match.MIXED_SCRIPT
    assert not match(s1, s2, None)
    assert not match(s1, s2, "rtl")


def test_public_names() -> None:
    assert {"skeleton", "match", "Match"} <= set(confusable.__all__)
