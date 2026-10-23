"""confusable_homoglyphs.categories: the script and category of characters.

The alias of a character is its script's name in Scripts.txt, in capitals,
such as "LATIN" or "COMMON". Its category is the General_Category that
Scripts.txt gives it, with every cased letter (Lu, Ll and Lt, written L& there)
as "L". Characters that Scripts.txt does not list are ("Unknown", "Zzzz").
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from functools import cache
from typing import Any

__all__ = ["alias", "aliases_categories", "category", "unique_aliases"]


@cache
def _ranges() -> tuple[list[int], tuple[tuple[int, int, int, int], ...]]:
    from confusable._data.homoglyphs import SCRIPT_RANGES

    return [first for first, *_ in SCRIPT_RANGES], SCRIPT_RANGES


# The parameter is called chr, as in confusable_homoglyphs, for callers that
# pass it by name.
def aliases_categories(chr: str) -> tuple[str, str]:
    """Return the script alias and the category of a character.

    >>> aliases_categories("A")
    ('LATIN', 'L')
    >>> aliases_categories("-")
    ('COMMON', 'Pd')
    """
    from confusable._data.homoglyphs import ALIASES, CATEGORIES

    firsts, ranges = _ranges()
    cp = ord(chr)
    n = bisect_right(firsts, cp) - 1
    if n >= 0 and cp <= ranges[n][1]:
        return ALIASES[ranges[n][2]], CATEGORIES[ranges[n][3]]
    return "Unknown", "Zzzz"


def alias(chr: str) -> str:
    """Return the script alias of a character, such as "LATIN"."""
    return aliases_categories(chr)[0]


def category(chr: str) -> str:
    """Return the category of a character, such as "L" or "Pd"."""
    return aliases_categories(chr)[1]


def unique_aliases(string: Iterable[str]) -> set[str]:
    """Return the set of the script aliases of the characters of string.

    >>> sorted(unique_aliases("ABC-"))
    ['COMMON', 'LATIN']
    """
    return {alias(c) for c in string}


def __getattr__(name: str) -> Any:
    """Provide categories_data, the package's data, built on first use."""
    if name == "categories_data":
        from confusable._data.homoglyphs import ALIASES, CATEGORIES, SCRIPT_RANGES

        return {
            "iso_15924_aliases": list(ALIASES),
            "categories": list(CATEGORIES),
            "code_points_ranges": [list(r) for r in SCRIPT_RANGES],
        }
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
