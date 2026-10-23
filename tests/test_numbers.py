"""has_mixed_numbers() beyond the conformance fixtures."""

import pytest

from confusable import has_mixed_numbers
from confusable._data.properties import DECIMAL_ZEROS
from confusable._numbers import decimal_zeros


@pytest.mark.parametrize(
    ("text", "mixed"),
    [
        ("", False),
        ("route66", False),
        ("\u0661\u0662", False),  # ARABIC-INDIC DIGITS ONE and TWO
        ("1\u0661", True),  # ASCII and Arabic-Indic
        ("\u0660\u06f0", True),  # Arabic-Indic and Extended Arabic-Indic
        ("\u09ea8", True),  # BENGALI DIGIT FOUR looks like 8
        ("\uff11\uff12", False),  # fullwidth digits are a system of their own
        ("1\uff12", True),
        ("x\u00b2", False),  # SUPERSCRIPT TWO is No, not a decimal digit
    ],
)
def test_mixed_numbers(text: str, mixed: bool) -> None:
    assert has_mixed_numbers(text) is mixed


def test_decimal_zeros() -> None:
    assert decimal_zeros("a1\u0661\u0662") == {"0", "\u0660"}
    assert decimal_zeros("abc") == frozenset()


@pytest.mark.parametrize("zero", DECIMAL_ZEROS)
def test_every_digit_maps_to_its_zero(zero: int) -> None:
    for digit in range(zero, zero + 10):
        assert decimal_zeros(chr(digit)) == {chr(zero)}
    # Just outside the system: nothing, or the zero of the next system.
    assert decimal_zeros(chr(zero - 1)) <= {chr(zero - 10)}
    assert decimal_zeros(chr(zero + 10)) <= {chr(zero + 10)}
