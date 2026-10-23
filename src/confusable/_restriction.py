"""Mixed-script and restriction-level detection (UTS #39 sections 5.1, 5.2)."""

from __future__ import annotations

import enum
from functools import reduce

from confusable import _identifiers, _scripts

# UAX #31 revision 45, Table 5: the Recommended scripts, without Common and
# Inherited. Bopomofo has been a Limited Use script since Unicode 17.
RECOMMENDED_SCRIPTS = frozenset(
    "Arab Armn Beng Cyrl Deva Ethi Geor Grek Gujr Guru Hang Hani Hebr Hira Kana "
    "Knda Khmr Laoo Latn Mlym Mymr Orya Sinh Taml Telu Thaa Thai Tibt".split()
)


class RestrictionLevel(enum.IntEnum):
    """The UTS #39 section 5.2 restriction levels, most restrictive first.

    The values are the levels' numbers in UTS #39, so a lower level is more
    restrictive: ``restriction_level(name) <= RestrictionLevel.HIGHLY_RESTRICTIVE``
    accepts the first three.
    """

    ASCII_ONLY = 1
    SINGLE_SCRIPT = 2
    HIGHLY_RESTRICTIVE = 3
    MODERATELY_RESTRICTIVE = 4
    MINIMALLY_RESTRICTIVE = 5
    UNRESTRICTED = 6


def is_mixed_script(text: str) -> bool:
    r"""Return whether text is mixed-script (UTS #39 section 5.1).

    Text is mixed-script when no script is shared by every character, once
    Common and Inherited characters (digits, punctuation, combining marks) are
    set aside and the CJK writing systems are taken into account: Han with
    Hiragana is single-script Japanese.

    >>> is_mixed_script("p\u0430ypal")  # with CYRILLIC SMALL LETTER A
    True
    >>> is_mixed_script("\u3006\u5207")  # Japanese: Han with Hiragana
    False
    """
    return _scripts.resolved_script_set(text) == frozenset()


def restriction_level(text: str) -> RestrictionLevel:
    r"""Return the UTS #39 section 5.2 restriction level of text.

    The identifier profile is the General Security Profile, under canonical
    equivalence (see is_allowed): text outside it is UNRESTRICTED.

    >>> restriction_level("paypal")
    <RestrictionLevel.ASCII_ONLY: 1>
    >>> restriction_level("caf\u00e9")
    <RestrictionLevel.SINGLE_SCRIPT: 2>
    >>> restriction_level("abc\u3042")  # Latin with Hiragana
    <RestrictionLevel.HIGHLY_RESTRICTIVE: 3>
    >>> restriction_level("p\u0430ypal")  # Latin with Cyrillic
    <RestrictionLevel.MINIMALLY_RESTRICTIVE: 5>
    >>> restriction_level("pay pal")  # a space is outside the profile
    <RestrictionLevel.UNRESTRICTED: 6>
    """
    if not _identifiers.is_allowed(text):
        return RestrictionLevel.UNRESTRICTED
    if text.isascii():
        return RestrictionLevel.ASCII_ONLY
    # The set of the characters' augmented script sets, the SOSS; None is ALL.
    soss = {_scripts.augmented_script_set(ord(c)) for c in text}
    if _scripts.resolved_script_set(text) != frozenset():
        return RestrictionLevel.SINGLE_SCRIPT
    # Leave out every entry that contains Latin, ALL included.
    rest = [entry for entry in soss if entry is not None and "Latn" not in entry]
    for writing_system in ("Kore", "Hanb", "Jpan"):
        if all(writing_system in entry for entry in rest):
            return RestrictionLevel.HIGHLY_RESTRICTIVE
    shared: frozenset[str] = reduce(frozenset.intersection, rest)
    if shared & (RECOMMENDED_SCRIPTS - {"Cyrl", "Grek"}):
        return RestrictionLevel.MODERATELY_RESTRICTIVE
    return RestrictionLevel.MINIMALLY_RESTRICTIVE
