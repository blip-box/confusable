"""restriction_level() and is_mixed_script() beyond the conformance fixtures."""

import pytest

from confusable import RestrictionLevel, is_mixed_script, restriction_level
from confusable._restriction import RECOMMENDED_SCRIPTS


def test_levels_are_ordered_most_restrictive_first() -> None:
    assert list(RestrictionLevel) == sorted(RestrictionLevel)
    assert RestrictionLevel.ASCII_ONLY < RestrictionLevel.UNRESTRICTED
    # The numbering UTS #39 section 5.2 uses.
    assert [level.value for level in RestrictionLevel] == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("", RestrictionLevel.ASCII_ONLY),
        ("abc\u6f22\u5b57", RestrictionLevel.SINGLE_SCRIPT),  # Latin + Han: Hntl
        ("abc\uac00", RestrictionLevel.HIGHLY_RESTRICTIVE),  # Latin + Hangul
        ("abc\u0915", RestrictionLevel.MODERATELY_RESTRICTIVE),  # + Devanagari
        ("abc\u03b1", RestrictionLevel.MINIMALLY_RESTRICTIVE),  # + Greek
        ("a\u09e6\u1040", RestrictionLevel.MINIMALLY_RESTRICTIVE),  # shared: Cakm
        ("abc\u200d", RestrictionLevel.UNRESTRICTED),  # ZWJ is outside the profile
    ],
)
def test_restriction_levels(text: str, level: RestrictionLevel) -> None:
    assert restriction_level(text) is level


@pytest.mark.parametrize(
    ("text", "mixed"),
    [
        ("", False),
        ("123!", False),  # Common only: every script
        ("abc\u0430", True),
        ("abc\u6f22", False),  # Hntl since UTS #39 revision 34
        ("\u306d\u30ac", False),  # Hiragana and Katakana: Japanese
    ],
)
def test_is_mixed_script(text: str, mixed: bool) -> None:
    assert is_mixed_script(text) is mixed


def test_recommended_scripts_follow_uax31_table_5() -> None:
    assert len(RECOMMENDED_SCRIPTS) == 28
    assert "Bopo" not in RECOMMENDED_SCRIPTS  # Limited Use since Unicode 17
