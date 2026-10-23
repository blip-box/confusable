"""Confusable detection: skeletons and the confusable classes (UTS #39 section 4)."""

from __future__ import annotations

import enum
import re
from typing import Literal

from confusable import _bidi, _scripts
from confusable._data import bidi as _bidi_data
from confusable._data import confusables as _confusables
from confusable._data import properties as _properties
from confusable._normalize import nfd

Direction = Literal["ltr", "rtl", "auto"]

# internalSkeleton steps 2 and 3 as one str.translate table: Default_Ignorable
# code points are removed, and every other character with a prototype becomes
# its prototype. Step 2 comes first, so the removal wins for the few
# ignorables that also have a prototype.
_MAPPING: dict[int, str | None] = dict(_confusables.PROTOTYPES)
for _first, _last in _properties.DEFAULT_IGNORABLE_RANGES:
    _MAPPING.update(dict.fromkeys(range(_first, _last + 1)))


def _character_class(classes: set[str]) -> re.Pattern[str]:
    """Compile a regex matching any code point whose Bidi_Class is in classes."""
    runs = _bidi_data.BIDI_CLASS_RUNS
    parts = []
    for n, (first, value) in enumerate(runs):
        if value in classes:
            last = runs[n + 1][0] - 1 if n + 1 < len(runs) else 0x10FFFF
            parts.append(f"\\U{first:08x}-\\U{last:08x}")
    return re.compile(f"[{''.join(parts)}]")


# Only these classes can put text at an odd embedding level in a
# left-to-right paragraph. Without any of them, display order is logical
# order and nothing is mirrored, so bidiSkeleton(LTR, X) is internalSkeleton(X).
# UTS #39 states this fast path with only R and AL, which is wrong: see
# confusable._bidi and test_uts39_fast_path_needs_more_than_r_and_al.
_ODD_LEVEL = _character_class({"R", "AL", "AN", "RLE", "RLO", "RLI"})


def _internal_skeleton(text: str) -> str:
    return nfd(nfd(text).translate(_MAPPING))


_BIDI_DIRECTION: dict[Direction, _bidi.Direction] = {
    "ltr": "LTR",
    "rtl": "RTL",
    "auto": "auto",
}


def skeleton(text: str, direction: Direction | None = "ltr") -> str:
    r"""Return the UTS #39 skeleton of text.

    Two strings are confusable when their skeletons are equal. A skeleton is
    for comparing, not for display, and it changes with the Unicode version
    (see ``confusable.unicode_version``), so recompute stored skeletons when
    that changes.

    direction is the paragraph direction text is displayed in: "ltr" (the
    default) gives UTS #39 skeleton(X), which is bidiSkeleton(LTR, X); "rtl"
    and "auto" (the direction of the first strong character) give
    bidiSkeleton(RTL, X) and bidiSkeleton(FS, X). None gives internalSkeleton,
    which ignores display order, as ICU's getSkeleton and UTS #39 revisions
    before 28 do.

    >>> skeleton("p\u0430ypal")  # with CYRILLIC SMALL LETTER A
    'paypal'
    >>> skeleton("invoice\u202egpj.exe")  # displays as invoiceexe.jpg
    'invoiceexe.jpg'
    """
    if direction is None:
        return _internal_skeleton(text)
    if direction not in _BIDI_DIRECTION:
        raise ValueError(
            f"direction must be 'ltr', 'rtl', 'auto' or None, not {direction!r}"
        )
    if direction == "ltr" and (text.isascii() or not _ODD_LEVEL.search(text)):
        return _internal_skeleton(text)
    return _internal_skeleton(_bidi.display(text, _BIDI_DIRECTION[direction]))


class Match(enum.Flag):
    """How two strings are confusable, per UTS #39 section 4.

    Every confusable pair is either SINGLE_SCRIPT or MIXED_SCRIPT; a
    WHOLE_SCRIPT pair is also MIXED_SCRIPT. An empty Match (``Match(0)``) is
    false: the strings are not confusable.
    """

    SINGLE_SCRIPT = enum.auto()
    """The strings' resolved script sets share a script, as "rn" and "m" do."""

    MIXED_SCRIPT = enum.auto()
    """The resolved script sets share no script."""

    WHOLE_SCRIPT = enum.auto()
    """Mixed-script, and each string is single-script on its own."""


def match(a: str, b: str, direction: Direction | None = "ltr") -> Match:
    r"""Return how a and b are confusable: an empty, false Match if they are not.

    a and b are confusable when their skeletons, for the given display
    direction (see skeleton), are equal. The result also says which class of
    confusable they are, from their resolved script sets.

    >>> match("paypal", "p\u0430ypal") == Match.MIXED_SCRIPT  # CYRILLIC A
    True
    >>> cyrillic_scope = "\u0455\u0441\u043e\u0440\u0435"
    >>> Match.WHOLE_SCRIPT in match("scope", cyrillic_scope)
    True
    >>> match("rn", "m") == Match.SINGLE_SCRIPT
    True
    >>> bool(match("paypal", "payqal"))
    False
    """
    if skeleton(a, direction) != skeleton(b, direction):
        return Match(0)
    scripts_a = _scripts.resolved_script_set(a)
    scripts_b = _scripts.resolved_script_set(b)
    if _scripts.intersects(scripts_a, scripts_b):
        return Match.SINGLE_SCRIPT
    if scripts_a != frozenset() and scripts_b != frozenset():
        return Match.MIXED_SCRIPT | Match.WHOLE_SCRIPT
    return Match.MIXED_SCRIPT
