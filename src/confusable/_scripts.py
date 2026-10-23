"""Augmented and resolved script sets (UTS #39 section 5.1).

A resolved script set is either a frozenset of ISO 15924 codes or ALL, the set
of all scripts, which characters with Script_Extensions {Common} or
{Inherited} contribute. ALL is represented by None.

The tables load on first use, so that importing the package stays fast.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import cache

from confusable._lookup import Runs

ScriptSet = frozenset[str] | None  # None is ALL, the set of all scripts.


@cache
def _script_runs() -> tuple[Runs, Runs]:
    """Return the Script and Script_Extensions runs."""
    from confusable._data.scripts import SCRIPT_EXTENSIONS_RUNS, SCRIPT_RUNS

    return Runs(SCRIPT_RUNS), Runs(SCRIPT_EXTENSIONS_RUNS)


# UTS #39 revision 34: the writing systems that span several scripts.
_AUGMENTATIONS = {
    "Hani": ("Hanb", "Hntl", "Jpan", "Kore"),
    "Hira": ("Jpan",),
    "Kana": ("Jpan",),
    "Hang": ("Kore",),
    "Bopo": ("Hanb",),
    "Latn": ("Hntl",),
}


@cache
def _augment(codes: str) -> ScriptSet:
    scripts = set(codes.split())
    if scripts & {"Zyyy", "Zinh"}:
        return None
    for script in list(scripts):
        scripts.update(_AUGMENTATIONS.get(script, ()))
    return frozenset(scripts)


def augmented_script_set(cp: int) -> ScriptSet:
    """Return a character's Script_Extensions, augmented per UTS #39 5.1."""
    script, extensions = _script_runs()
    return _augment(extensions[cp] or script[cp])


def resolved_script_set(text: Iterable[str]) -> ScriptSet:
    """Return the intersection of the characters' augmented script sets.

    The empty string, and text made only of Common and Inherited characters,
    resolve to ALL (None).
    """
    resolved: ScriptSet = None
    for c in text:
        augmented = augmented_script_set(ord(c))
        if augmented is None:
            continue
        resolved = augmented if resolved is None else resolved & augmented
        if not resolved:
            break
    return resolved


def intersects(a: ScriptSet, b: ScriptSet) -> bool:
    """Return whether two script sets have at least one script in common."""
    if a is None:
        return b is None or bool(b)
    if b is None:
        return bool(a)
    return not a.isdisjoint(b)
