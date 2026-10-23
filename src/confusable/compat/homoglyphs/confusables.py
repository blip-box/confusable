"""confusable_homoglyphs.confusables: mixed scripts and homoglyphs.

These are confusable_homoglyphs' own heuristics, kept for compatibility. A
character is confusable when confusables.txt pairs it with another character
or sequence, in either direction; UTS #39 skeletons, which confusable.match
compares, are more precise.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import cache
from typing import Any, Literal, TypedDict

from confusable.compat.homoglyphs.categories import alias, unique_aliases

__all__ = ["Found", "is_confusable", "is_dangerous", "is_mixed_script"]


class Homoglyph(TypedDict):
    """A character or sequence that looks like another, and its name."""

    c: str
    n: str


class Confusable(TypedDict):
    """A confusable character of a string, as is_confusable reports it."""

    character: str
    alias: str
    homoglyphs: list[Homoglyph]


class Found(Exception):  # noqa: N818 (its name in confusable_homoglyphs)
    """Raised and caught inside confusable_homoglyphs; kept for its users."""


@cache
def _homoglyphs() -> dict[str, tuple[tuple[str, str], ...]]:
    """Map each character or sequence to its homoglyphs and their names.

    In the order of confusables.txt, as confusable_homoglyphs builds them.
    """
    from confusable._data.homoglyphs import NAMES, PAIRS

    homoglyphs: dict[str, list[tuple[str, str]]] = {}
    for source, target in PAIRS:
        homoglyphs.setdefault(source, []).append((target, NAMES[target]))
        homoglyphs.setdefault(target, []).append((source, NAMES[source]))
    return {key: tuple(value) for key, value in homoglyphs.items()}


def _listed(found: tuple[tuple[str, str], ...]) -> list[Homoglyph]:
    return [{"c": c, "n": n} for c, n in found]


def is_mixed_script(
    string: Iterable[str], allowed_aliases: Iterable[str] = ("COMMON",)
) -> bool:
    """Return whether string uses more than one script alias.

    Aliases in allowed_aliases (any case) do not count, COMMON by default.

    >>> (
    ...     is_mixed_script("Abc"),
    ...     is_mixed_script("Ab\u03c4"),
    ... )  # with GREEK SMALL LETTER TAU
    (False, True)
    """
    allowed = {a.upper() for a in allowed_aliases}
    return len(unique_aliases(string) - allowed) > 1


def is_confusable(
    string: Iterable[str],
    greedy: bool = False,
    preferred_aliases: Iterable[str] = (),
) -> list[Confusable] | Literal[False]:
    """Return the characters of string that have homoglyphs, or False.

    With preferred_aliases, such as ["latin"], only characters from other
    scripts count, and only if one of their homoglyphs uses a preferred
    script. Without greedy, the list stops at the first character found.

    >>> found = is_confusable("pa\u03c1a", preferred_aliases=["latin"])  # GREEK RHO
    >>> [(f["character"], f["alias"]) for f in found] == [("\u03c1", "GREEK")]
    True
    >>> is_confusable("Ab\u00e7", preferred_aliases=["latin"])
    False
    """
    preferred = [a.upper() for a in preferred_aliases]
    homoglyphs = _homoglyphs()
    outputs: list[Confusable] = []
    checked = set()
    for char in string:
        if char in checked:
            continue
        checked.add(char)
        char_alias = alias(char)
        if char_alias in preferred:
            continue
        found = homoglyphs.get(char)
        if found is None:
            continue
        # With preferred aliases, a character counts only if one of its
        # homoglyphs has a character from a preferred script.
        if preferred and not any(
            alias(glyph) in preferred for homoglyph, _ in found for glyph in homoglyph
        ):
            continue
        output: Confusable = {
            "character": char,
            "alias": char_alias,
            "homoglyphs": _listed(found),
        }
        if not greedy:
            return [output]
        outputs.append(output)
    return outputs or False


def is_dangerous(string: Iterable[str], preferred_aliases: Iterable[str] = ()) -> bool:
    """Return whether string is mixed-script and has confusable characters.

    >>> is_dangerous("Allo"), is_dangerous("Allo\u03c1")  # with GREEK RHO
    (False, True)
    """
    return is_mixed_script(string) and bool(
        is_confusable(string, preferred_aliases=preferred_aliases)
    )


def __getattr__(name: str) -> Any:
    """Provide confusables_data, the package's data, built on first use."""
    if name == "confusables_data":
        return {key: _listed(found) for key, found in _homoglyphs().items()}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
