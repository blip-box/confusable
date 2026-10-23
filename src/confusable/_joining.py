"""Joining controls in limited contexts (UTS #39 section 3.1.1.1).

ZERO WIDTH NON-JOINER (ZWNJ) and ZERO WIDTH JOINER (ZWJ) are outside the
General Security Profile, but some languages need them: Persian breaks a
cursive connection with ZWNJ, and Malayalam and Sinhala form conjuncts with
them. UTS #39 allows them only where they make a visible difference:

- A1, ZWNJ breaking a cursive connection: /$LJ $T* ZWNJ $RJ/, by Joining_Type.
- A2, ZWNJ in a conjunct: /$L $M* $V $M1* ZWNJ $M1* $L/.
- B, ZWJ in a conjunct: /$L $M* $V $M1* ZWJ (?!$D)/.

$L is a letter, $V a virama (Canonical_Combining_Class=Virama), $M a
nonspacing mark (gc=Mn), $M1 a nonspacing mark with a nonzero combining class,
and $D a dependent vowel (Indic_Syllabic_Category=Vowel_Dependent). Each
matched sequence must be single-script, and the test runs on the NFC form.
"""

from __future__ import annotations

from collections.abc import Iterator

from confusable import _scripts
from confusable._data import joining as _joining
from confusable._data import normalization as _normalization
from confusable._data import properties as _properties
from confusable._lookup import Ranges, Runs
from confusable._normalize import nfc

ZWNJ = chr(0x200C)
ZWJ = chr(0x200D)
JOINERS = (ZWNJ, ZWJ)

_JOINING_TYPE = Runs(_joining.JOINING_TYPE_RUNS)
_VOWEL_DEPENDENT = Ranges(_joining.VOWEL_DEPENDENT_RANGES)
_CATEGORY = Runs(_properties.GENERAL_CATEGORY_RUNS)
_COMBINING_CLASS = _normalization.CANONICAL_COMBINING_CLASS
_VIRAMA = 9

_LEFT_JOINING = ("D", "L")  # $LJ: joins to the character after it
_RIGHT_JOINING = ("D", "R")  # $RJ: joins to the character before it


def _letter(c: str) -> bool:
    return _CATEGORY[ord(c)][0] == "L"


def _nonspacing(c: str) -> bool:
    return _CATEGORY[ord(c)] == "Mn"


def _combining_nonspacing(c: str) -> bool:
    """$M1: a nonspacing mark with a nonzero canonical combining class."""
    return _nonspacing(c) and ord(c) in _COMBINING_CLASS


def _single_script(sequence: str) -> bool:
    """Whether the sequence is single-script in the sense of section 5.1."""
    return _scripts.resolved_script_set(sequence) != frozenset()


def _breaks_cursive_connection(text: str, i: int) -> bool:
    """A1: the ZWNJ at i matches /$LJ $T* ZWNJ $RJ/."""
    if i + 1 == len(text) or _JOINING_TYPE[ord(text[i + 1])] not in _RIGHT_JOINING:
        return False
    start = i - 1
    while start >= 0 and _JOINING_TYPE[ord(text[start])] == "T":
        start -= 1
    return (
        start >= 0
        and _JOINING_TYPE[ord(text[start])] in _LEFT_JOINING
        and _single_script(text[start : i + 2])
    )


def _conjunct_starts(text: str, i: int) -> Iterator[int]:
    """Yield the start of each match of /$L $M* $V $M1*/ that ends at i."""
    virama = i - 1
    while virama >= 0:
        c = text[virama]
        if _COMBINING_CLASS.get(ord(c)) == _VIRAMA:
            start = virama - 1
            while start >= 0 and _nonspacing(text[start]):
                start -= 1
            if start >= 0 and _letter(text[start]):
                yield start
        # Between the virama and i there may only be $M1 marks, and a virama
        # can be one of them, so keep looking further back past each.
        if not _combining_nonspacing(c):
            return
        virama -= 1


def _non_joiner_in_conjunct(text: str, i: int) -> bool:
    """A2: the ZWNJ at i matches /$L $M* $V $M1* ZWNJ $M1* $L/."""
    end = i + 1
    while end < len(text) and _combining_nonspacing(text[end]):
        end += 1
    if end == len(text) or not _letter(text[end]):
        return False
    return any(
        _single_script(text[start : end + 1]) for start in _conjunct_starts(text, i)
    )


def _joiner_in_conjunct(text: str, i: int) -> bool:
    """B: the ZWJ at i matches /$L $M* $V $M1* ZWJ (?!$D)/."""
    if i + 1 < len(text) and ord(text[i + 1]) in _VOWEL_DEPENDENT:
        return False
    return any(
        _single_script(text[start : i + 1]) for start in _conjunct_starts(text, i)
    )


def joining_controls_in_context(text: str) -> list[bool]:
    """For each ZWNJ and ZWJ in text, in order, whether its context allows it.

    The contexts are tested on the NFC form of the text, as section 3.1.1.1
    says. Normalization never moves, adds or removes a joining control, so the
    results line up with the joining controls of the text as given.
    """
    if ZWNJ not in text and ZWJ not in text:
        return []
    composed = nfc(text)
    return [in_context(composed, i) for i, c in enumerate(composed) if c in JOINERS]


def in_context(composed: str, i: int) -> bool:
    """Whether the ZWNJ or ZWJ at i of NFC text is in an A1, A2 or B context."""
    if composed[i] == ZWNJ:
        return _breaks_cursive_connection(composed, i) or _non_joiner_in_conjunct(
            composed, i
        )
    return _joiner_in_conjunct(composed, i)
