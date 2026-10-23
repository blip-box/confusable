"""Identifier checks (UTS #39 section 3.1, UAX #31).

The General Security Profile for identifiers allows the characters with
Identifier_Status=Allowed, under canonical equivalence; Identifier_Type says
why each character has its status. XID_Start and XID_Continue are the UAX #31
identifier properties, as Python 3.15's unicodedata.isxidstart() and
isxidcontinue() report them, here at the pinned Unicode version on any Python.
"""

from __future__ import annotations

import enum
from collections.abc import Iterator

from confusable import _joining
from confusable._data import identifiers as _data
from confusable._data.normalization import (
    CANONICAL_COMBINING_CLASS,
    CANONICAL_COMPOSITION,
)
from confusable._lookup import Ranges, Runs
from confusable._normalize import nfc, nfd

_ALLOWED = Ranges(_data.IDENTIFIER_ALLOWED_RANGES)
_TYPES = Runs(_data.IDENTIFIER_TYPE_RUNS)
_XID_START = Ranges(_data.XID_START_RANGES)
_XID_CONTINUE = Ranges(_data.XID_CONTINUE_RANGES)

# Starters that can compose with the character before them: the second half
# of a primary composite, and the Hangul vowel and trailing jamo.
_COMBINES_BACKWARD = frozenset(
    {second for _, second in CANONICAL_COMPOSITION}
    | set(range(0x1161, 0x1176))
    | set(range(0x11A8, 0x11C3))
)


class IdentifierStatus(enum.Enum):
    """A character's Identifier_Status (UTS #39 section 3.1)."""

    ALLOWED = "Allowed"
    RESTRICTED = "Restricted"


class IdentifierType(enum.Enum):
    """Why a character has its Identifier_Status (UTS #39 Table 1).

    RECOMMENDED and INCLUSION make a character Allowed; any other type makes
    it Restricted.
    """

    NOT_CHARACTER = "Not_Character"
    DEPRECATED = "Deprecated"
    DEFAULT_IGNORABLE = "Default_Ignorable"
    NOT_NFKC = "Not_NFKC"
    NOT_XID = "Not_XID"
    EXCLUSION = "Exclusion"
    OBSOLETE = "Obsolete"
    TECHNICAL = "Technical"
    UNCOMMON_USE = "Uncommon_Use"
    LIMITED_USE = "Limited_Use"
    INCLUSION = "Inclusion"
    RECOMMENDED = "Recommended"


def _code_point(char: str, function: str) -> int:
    if not isinstance(char, str) or len(char) != 1:
        raise TypeError(f"{function}() takes a single character, not {char!r}")
    return ord(char)


def identifier_status(char: str) -> IdentifierStatus:
    r"""Return the Identifier_Status of a single character.

    >>> identifier_status("a")
    <IdentifierStatus.ALLOWED: 'Allowed'>
    >>> identifier_status("\u200d")  # ZERO WIDTH JOINER
    <IdentifierStatus.RESTRICTED: 'Restricted'>
    """
    if _code_point(char, "identifier_status") in _ALLOWED:
        return IdentifierStatus.ALLOWED
    return IdentifierStatus.RESTRICTED


def identifier_types(char: str) -> frozenset[IdentifierType]:
    r"""Return the Identifier_Type values of a single character.

    >>> sorted(t.value for t in identifier_types("\u0114"))
    ['Uncommon_Use']
    >>> sorted(t.value for t in identifier_types("\u200d"))
    ['Default_Ignorable']
    """
    types = _TYPES[_code_point(char, "identifier_types")]
    return frozenset(IdentifierType(name) for name in types.split())


def isxidstart(char: str) -> bool:
    """Return whether a single character has the XID_Start property (UAX #31)."""
    return _code_point(char, "isxidstart") in _XID_START


def isxidcontinue(char: str) -> bool:
    """Return whether a single character has XID_Continue (UAX #31)."""
    return _code_point(char, "isxidcontinue") in _XID_CONTINUE


def _segments(decomposed: str) -> Iterator[str]:
    """Split NFD text where composition cannot reach across."""
    start = 0
    for i, c in enumerate(decomposed):
        cp = ord(c)
        if (
            i > start
            and cp not in CANONICAL_COMBINING_CLASS
            and cp not in _COMBINES_BACKWARD
        ):
            yield decomposed[start:i]
            start = i
    yield decomposed[start:]


def is_allowed(text: str, *, joining_controls: bool = False) -> bool:
    r"""Return whether text is within the General Security Profile.

    Canonical equivalence applies (UTS #39 section 3.1): each segment of the
    text passes if all its characters are Allowed in either its decomposed
    (NFD) or its composed (NFC) form. So the answer is the same however the
    text is encoded, and an attacker cannot pick the encoding that passes.

    The profile excludes ZERO WIDTH JOINER and ZERO WIDTH NON-JOINER, which
    some languages need. With joining_controls=True, they are allowed where
    UTS #39 section 3.1.1.1 says they make a visible difference, as in
    Persian, Malayalam and Sinhala words, and nowhere else. UTS #39 calls
    this a modification of the profile, so say so where you document yours.

    >>> is_allowed("paypal")
    True
    >>> is_allowed("pay pal")  # a space is Restricted
    False
    >>> # U+0114 is Restricted, but E with a combining breve is Allowed:
    >>> is_allowed("\u0114"), is_allowed("E\u0306")
    (True, True)
    >>> persian = "\u0646\u0627\u0645\u0647\u200c\u0627\u06cc"  # with a ZWNJ
    >>> is_allowed(persian), is_allowed(persian, joining_controls=True)
    (False, True)
    """
    if text.isascii():
        return all(ord(c) in _ALLOWED for c in text)
    # Each joining control starts a segment of its own, in text order.
    in_context = iter(
        _joining.joining_controls_in_context(text) if joining_controls else ()
    )
    for segment in _segments(nfd(text)):
        if joining_controls and segment[0] in (_joining.ZWNJ, _joining.ZWJ):
            if not next(in_context):
                return False
            segment = segment[1:]
        if not (
            all(ord(c) in _ALLOWED for c in segment)
            or all(ord(c) in _ALLOWED for c in nfc(segment))
        ):
            return False
    return True
