"""Mixed-number detection (UTS #39 section 5.3).

The table loads on first use, so that importing the package stays fast.
"""

from __future__ import annotations

from bisect import bisect_right
from functools import cache


@cache
def _system_zeros() -> tuple[int, ...]:
    """Return the zero of each decimal number system, sorted.

    Each system is the ten code points from its zero, so the digits are
    exactly the code points less than ten above a zero.
    """
    from confusable._data.properties import DECIMAL_ZEROS

    return DECIMAL_ZEROS


def decimal_zeros(text: str) -> frozenset[str]:
    """Return the zero digit of each decimal number system used in text.

    A decimal digit is a character with General_Category Decimal_Number (Nd).
    No canonical decomposition contains one, so the result is the same for
    every normalization form of the text.
    """
    system_zeros = _system_zeros()
    zeros = set()
    for c in text:
        cp = ord(c)
        n = bisect_right(system_zeros, cp) - 1
        if n >= 0 and cp - system_zeros[n] < 10:
            zeros.add(chr(system_zeros[n]))
    return frozenset(zeros)


def has_mixed_numbers(text: str) -> bool:
    r"""Return whether text mixes digits of different decimal number systems.

    Digits of different systems can look alike: U+0660 ARABIC-INDIC DIGIT
    ZERO and U+06F0 EXTENDED ARABIC-INDIC DIGIT ZERO, or U+09EA BENGALI DIGIT
    FOUR and the ASCII digit 8. UTS #39 section 5.3 therefore rejects text
    whose digits come from more than one system.

    >>> has_mixed_numbers("route66")
    False
    >>> has_mixed_numbers("\u0967\u0968\u0969")  # DEVANAGARI DIGITS ONE TO THREE
    False
    >>> has_mixed_numbers("\u09ea\u09ea8")  # BENGALI DIGIT FOUR twice, then 8
    True
    """
    if text.isascii():
        return False
    return len(decimal_zeros(text)) > 1
