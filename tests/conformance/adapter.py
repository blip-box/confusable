"""The library under test, as the conformance tests see it.

The conformance tests are written against the operations that UTS #39,
UAX #29 and UAX #15 define, not against confusable's public API, which is
designed after this harness. Each function here maps one operation to the
library and converts the result to the fixture representation.

Until the library implements an operation, its function raises
NotImplementedYetError and the tests that need it are strict xfails (see
test_conformance.py). Wiring an operation to a wrong implementation fails
those tests outright, and making them pass without removing the xfail marker
fails them too, so the marker cannot go stale.
"""

from __future__ import annotations

from typing import Literal

import confusable
from confusable import _bidi, _normalize, _scripts
from confusable._data import bidi as _bidi_data
from confusable._data import graphemes as _graphemes
from confusable._data import normalization as _normalization
from confusable._data import properties as _properties
from confusable._data import scripts as _scripts_data
from confusable._lookup import Ranges, Runs


class NotImplementedYetError(NotImplementedError):
    """The library does not implement this operation yet."""


def skeleton(text: str) -> str:
    """UTS #39 skeleton(X), which is bidiSkeleton(LTR, X)."""
    return confusable.skeleton(text)


def internal_skeleton(text: str) -> str:
    """UTS #39 internalSkeleton(X): skeleton without the bidi steps."""
    return confusable.skeleton(text, None)


def bidi_skeleton(text: str, direction: Literal["LTR", "RTL"]) -> str:
    """UTS #39 bidiSkeleton(direction, X)."""
    return confusable.skeleton(text, "ltr" if direction == "LTR" else "rtl")


def bidi_paragraph(
    text: str, direction: Literal["LTR", "RTL", "auto"]
) -> tuple[int, tuple[int | None, ...], tuple[int, ...]]:
    """UAX #9 through rule L2, as BidiCharacterTest.txt states the results.

    Returns the paragraph level, the resolved level of each character (None
    for those rule X9 removes), and the visual order of the others.
    """
    code_points = [ord(c) for c in text]
    types = [_bidi.bidi_class(cp) for cp in code_points]
    level, levels, order = _bidi.levels_and_order(types, direction, code_points)
    return level, tuple(levels), tuple(order)


def bidi_classes(
    classes: tuple[str, ...], direction: Literal["LTR", "RTL", "auto"]
) -> tuple[tuple[int | None, ...], tuple[int, ...]]:
    """UAX #9 through rule L2 on Bidi_Class values, as in BidiTest.txt."""
    _, levels, order = _bidi.levels_and_order(classes, direction)
    return tuple(levels), tuple(order)


def bidi_display(text: str, direction: Literal["LTR", "RTL"]) -> str:
    """R'' of UTS #39 bidiSkeleton: display order with UAX #9 L3 and L4."""
    return _bidi.display(text, direction)


def nfd(text: str) -> str:
    """NFD at the pinned Unicode version, independent of Python's own."""
    return _normalize.nfd(text)


def nfc(text: str) -> str:
    """NFC at the pinned Unicode version, independent of Python's own."""
    return _normalize.nfc(text)


def resolved_script_set(text: str) -> str:
    """UTS #39 section 5.1 resolved script set.

    Returned in fixture form: sorted ISO 15924 codes joined by spaces, "ALL"
    for the set of all scripts, or "" for the empty set.
    """
    resolved = _scripts.resolved_script_set(text)
    return "ALL" if resolved is None else " ".join(sorted(resolved))


def restriction_level(text: str) -> str:
    """UTS #39 section 5.2 restriction level, as in the fixtures.

    One of ASCII_ONLY, SINGLE_SCRIPT, HIGHLY_RESTRICTIVE,
    MODERATELY_RESTRICTIVE, MINIMALLY_RESTRICTIVE or UNRESTRICTED, using the
    General Security Profile as the identifier profile.
    """
    return confusable.restriction_level(text).name


def confusable_classes(
    a: str, b: str, skeleton: Literal["skeleton", "internal", "rtl"] = "skeleton"
) -> frozenset[str]:
    """UTS #39 section 4 classes for a pair, under one skeleton function.

    A subset of {"SINGLE_SCRIPT", "MIXED_SCRIPT", "WHOLE_SCRIPT"}; empty when
    the two strings are not confusable.
    """
    result = confusable.match(a, b, _MATCH_DIRECTION[skeleton])
    if result is None:
        return frozenset()
    # UTS #39 counts every whole-script confusable as mixed-script too.
    if result is confusable.Match.WHOLE_SCRIPT:
        return frozenset({"MIXED_SCRIPT", "WHOLE_SCRIPT"})
    return frozenset({result.name})


_MATCH_DIRECTION: dict[str, Literal["ltr", "rtl"] | None] = {
    "skeleton": "ltr",
    "internal": None,
    "rtl": "rtl",
}


def outside_profile(text: str) -> bool:
    """True if the text is outside the General Security Profile."""
    return not confusable.is_allowed(text)


def repeated_nonspacing_mark(text: str) -> bool:
    """UTS #39 section 5.4: the same nonspacing mark twice in one sequence."""
    raise NotImplementedYetError("repeated_nonspacing_mark")


def hidden_overlay(text: str) -> bool:
    """UTS #39 section 5.4: a nonspacing mark hidden by its base character."""
    raise NotImplementedYetError("hidden_overlay")


def decimal_zeros(text: str) -> frozenset[str]:
    """UTS #39 section 5.3: the zero digit of each decimal system in the text."""
    raise NotImplementedYetError("decimal_zeros")


def grapheme_boundaries(text: str) -> tuple[int, ...]:
    """UAX #29 extended grapheme cluster boundaries, as code point offsets."""
    raise NotImplementedYetError("grapheme_boundaries")


_SCRIPT = Runs(_scripts_data.SCRIPT_RUNS)
_SCRIPT_EXTENSIONS = Runs(_scripts_data.SCRIPT_EXTENSIONS_RUNS)
_ENUMERATED = {
    "Script": _SCRIPT,
    "General_Category": Runs(_properties.GENERAL_CATEGORY_RUNS),
    "Grapheme_Cluster_Break": Runs(_graphemes.GRAPHEME_CLUSTER_BREAK_RUNS),
    "Indic_Conjunct_Break": Runs(_graphemes.INDIC_CONJUNCT_BREAK_RUNS),
}
_BINARY = {
    "Default_Ignorable_Code_Point": Ranges(_properties.DEFAULT_IGNORABLE_RANGES),
    "Bidi_Control": Ranges(_properties.BIDI_CONTROL_RANGES),
    "Join_Control": Ranges(_properties.JOIN_CONTROL_RANGES),
    "Extended_Pictographic": Ranges(_graphemes.EXTENDED_PICTOGRAPHIC_RANGES),
}


def property_value(name: str, cp: int) -> str:
    """A character property as properties.txt writes it.

    Names and value formats follow the fixture: ISO 15924 codes for Script,
    sorted codes for Script_Extensions ("" where it is just {Script}), "Y" or
    "N" for binary properties, sorted type names for Identifier_Type, hex for
    Bidi_Mirroring_Glyph and Bidi_Paired_Bracket ("" where there is none).
    """
    # The public API, for the properties it exposes.
    if name == "Identifier_Status":
        return confusable.identifier_status(chr(cp)).value
    if name == "Identifier_Type":
        return " ".join(sorted(t.value for t in confusable.identifier_types(chr(cp))))
    if name == "XID_Start":
        return "Y" if confusable.isxidstart(chr(cp)) else "N"
    if name == "XID_Continue":
        return "Y" if confusable.isxidcontinue(chr(cp)) else "N"
    if name in _ENUMERATED:
        return _ENUMERATED[name][cp]
    if name in _BINARY:
        return "Y" if cp in _BINARY[name] else "N"
    if name == "Script_Extensions":
        extensions = _SCRIPT_EXTENSIONS[cp]
        return "" if extensions in ("", _SCRIPT[cp]) else extensions
    if name == "Canonical_Combining_Class":
        return str(_normalization.CANONICAL_COMBINING_CLASS.get(cp, 0))
    if name == "Bidi_Class":
        return _bidi.bidi_class(cp)
    if name == "Bidi_Mirroring_Glyph":
        glyph = _bidi_data.BIDI_MIRRORING_GLYPH.get(cp)
        return "" if glyph is None else f"{glyph:04X}"
    if name == "Bidi_Paired_Bracket":
        bracket = _bidi_data.BIDI_BRACKETS.get(cp)
        return "" if bracket is None else f"{bracket[0]:04X}"
    if name == "Bidi_Paired_Bracket_Type":
        bracket = _bidi_data.BIDI_BRACKETS.get(cp)
        return {"o": "Open", "c": "Close"}[bracket[1]] if bracket else "None"
    raise NotImplementedYetError(f"property_value({name})")
