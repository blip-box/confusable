"""Identifier checks (UTS #39 section 3.1, UAX #31).

The General Security Profile for identifiers allows the characters with
Identifier_Status=Allowed, under canonical equivalence; Identifier_Type says
why each character has its status. XID_Start and XID_Continue are the UAX #31
identifier properties, as Python 3.15's unicodedata.isxidstart() and
isxidcontinue() report them, here at the pinned Unicode version on any Python.

The tables load on first use, so that importing the package stays fast.
"""

from __future__ import annotations

import enum
from collections.abc import Iterator
from functools import cache

from confusable import _joining
from confusable._lookup import Ranges, Runs
from confusable._normalize import combining_classes, compositions, nfc, nfd


@cache
def _allowed() -> Ranges:
    from confusable._data.identifiers import IDENTIFIER_ALLOWED_RANGES

    return Ranges(IDENTIFIER_ALLOWED_RANGES)


@cache
def _types() -> Runs:
    from confusable._data.identifiers import IDENTIFIER_TYPE_RUNS

    return Runs(IDENTIFIER_TYPE_RUNS)


@cache
def _xid_start() -> Ranges:
    from confusable._data.identifiers import XID_START_RANGES

    return Ranges(XID_START_RANGES)


@cache
def _xid_continue() -> Ranges:
    from confusable._data.identifiers import XID_CONTINUE_RANGES

    return Ranges(XID_CONTINUE_RANGES)


@cache
def _combines_backward() -> frozenset[int]:
    """Return the starters that can compose with the character before them.

    They are the second half of a primary composite, and the Hangul vowel and
    trailing jamo.
    """
    return frozenset(
        {second for _, second in compositions()}
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
    if _code_point(char, "identifier_status") in _allowed():
        return IdentifierStatus.ALLOWED
    return IdentifierStatus.RESTRICTED


def identifier_types(char: str) -> frozenset[IdentifierType]:
    r"""Return the Identifier_Type values of a single character.

    >>> sorted(t.value for t in identifier_types("\u0114"))
    ['Uncommon_Use']
    >>> sorted(t.value for t in identifier_types("\u200d"))
    ['Default_Ignorable']
    """
    types = _types()[_code_point(char, "identifier_types")]
    return frozenset(IdentifierType(name) for name in types.split())


def isxidstart(char: str) -> bool:
    """Return whether a single character has the XID_Start property (UAX #31)."""
    return _code_point(char, "isxidstart") in _xid_start()


def isxidcontinue(char: str) -> bool:
    """Return whether a single character has XID_Continue (UAX #31)."""
    return _code_point(char, "isxidcontinue") in _xid_continue()


def _segments(decomposed: str) -> Iterator[str]:
    """Split NFD text where composition cannot reach across."""
    classes = combining_classes()
    combines_backward = _combines_backward()
    start = 0
    for i, c in enumerate(decomposed):
        cp = ord(c)
        if i > start and cp not in classes and cp not in combines_backward:
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
    allowed = _allowed()
    if text.isascii():
        return all(ord(c) in allowed for c in text)
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
            all(ord(c) in allowed for c in segment)
            or all(ord(c) in allowed for c in nfc(segment))
        ):
            return False
    return True
