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


class NotImplementedYetError(NotImplementedError):
    """The library does not implement this operation yet."""


def skeleton(text: str) -> str:
    """UTS #39 skeleton(X), which is bidiSkeleton(LTR, X)."""
    raise NotImplementedYetError("skeleton")


def internal_skeleton(text: str) -> str:
    """UTS #39 internalSkeleton(X): skeleton without the bidi steps."""
    raise NotImplementedYetError("internal_skeleton")


def bidi_skeleton(text: str, direction: Literal["LTR", "RTL"]) -> str:
    """UTS #39 bidiSkeleton(direction, X)."""
    raise NotImplementedYetError("bidi_skeleton")


def nfd(text: str) -> str:
    """NFD at the pinned Unicode version, independent of Python's own."""
    raise NotImplementedYetError("nfd")


def resolved_script_set(text: str) -> str:
    """UTS #39 section 5.1 resolved script set.

    Returned in fixture form: sorted ISO 15924 codes joined by spaces, "ALL"
    for the set of all scripts, or "" for the empty set.
    """
    raise NotImplementedYetError("resolved_script_set")


def restriction_level(text: str) -> str:
    """UTS #39 section 5.2 restriction level, as in the fixtures.

    One of ASCII_ONLY, SINGLE_SCRIPT, HIGHLY_RESTRICTIVE,
    MODERATELY_RESTRICTIVE, MINIMALLY_RESTRICTIVE or UNRESTRICTED, using the
    General Security Profile as the identifier profile.
    """
    raise NotImplementedYetError("restriction_level")


def confusable_classes(
    a: str, b: str, skeleton: Literal["skeleton", "internal", "rtl"] = "skeleton"
) -> frozenset[str]:
    """UTS #39 section 4 classes for a pair, under one skeleton function.

    A subset of {"SINGLE_SCRIPT", "MIXED_SCRIPT", "WHOLE_SCRIPT"}; empty when
    the two strings are not confusable.
    """
    raise NotImplementedYetError("confusable_classes")


def outside_profile(text: str) -> bool:
    """True if any character is outside the General Security Profile."""
    raise NotImplementedYetError("outside_profile")


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


def property_value(name: str, cp: int) -> str:
    """A character property as properties.txt writes it.

    Names and value formats follow the fixture: ISO 15924 codes for Script,
    sorted codes for Script_Extensions ("" where it is just {Script}), "Y" or
    "N" for binary properties, sorted type names for Identifier_Type, hex for
    Bidi_Mirroring_Glyph and Bidi_Paired_Bracket ("" where there is none).
    """
    raise NotImplementedYetError("property_value")
