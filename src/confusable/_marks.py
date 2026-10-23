"""Checks on combining marks (UTS #39 section 5.4).

Both checks look at the text in NFD, so that canonically equivalent strings,
which are the same text written two ways, get the same answer.

The tables load on first use, so that importing the package stays fast.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import cache

from confusable._lookup import Runs
from confusable._normalize import combining_classes, nfd

# UTS #39 section 5.4: "Forbid sequences of more than 4 nonspacing marks".
MAX_NONSPACING_MARKS = 4


@cache
def _categories() -> Runs:
    from confusable._data.properties import GENERAL_CATEGORY_RUNS

    return Runs(GENERAL_CATEGORY_RUNS)


@cache
def _prototypes() -> dict[int, str]:
    from confusable._data.confusables import PROTOTYPES

    return PROTOTYPES


@cache
def _dotted_looking() -> frozenset[int]:
    """Return the characters that lose their dot under an accent above.

    ICU's isIllegalCombiningDotLeadCharacterNoLookup: i, j, l, dotless i and
    j, and the Soft_Dotted characters.
    """
    from confusable._data.properties import SOFT_DOTTED_RANGES

    return frozenset(
        {ord("i"), ord("j"), ord("l"), 0x0131, 0x0237}.union(
            *(range(first, last + 1) for first, last in SOFT_DOTTED_RANGES)
        )
    )


def _nonspacing_runs(decomposed: str) -> Iterator[list[str]]:
    """Yield each maximal run of nonspacing marks, gc=Mn or gc=Me."""
    categories = _categories()
    run: list[str] = []
    for c in decomposed:
        if categories[ord(c)] in ("Mn", "Me"):
            run.append(c)
        elif run:
            yield run
            run = []
    if run:
        yield run


def has_repeated_mark(text: str) -> bool:
    """Return whether a run of nonspacing marks in text repeats a mark.

    This is ICU's INVISIBLE check: the run need not repeat the mark at once,
    as in e, acute, grave, acute.
    """
    if text.isascii():
        return False
    return any(len(set(run)) < len(run) for run in _nonspacing_runs(nfd(text)))


def has_unlikely_marks(text: str) -> bool:
    r"""Return whether text has an unlikely sequence of combining marks.

    UTS #39 section 5.4 suggests forbidding a run of nonspacing marks
    (General_Category Mn or Me) that repeats a mark, which draws the mark on
    top of itself, or that has more than four marks, as "Zalgo" text does.

    >>> has_unlikely_marks(
    ...     "\u1ec7"
    ... )  # LATIN SMALL LETTER E WITH CIRCUMFLEX AND DOT BELOW
    False
    >>> has_unlikely_marks("e\u0301\u0301")  # two COMBINING ACUTE ACCENTs
    True
    >>> has_unlikely_marks("z\u0300\u0301\u0302\u0303\u0304")  # five marks
    True
    """
    if text.isascii():
        return False
    return any(
        len(run) > MAX_NONSPACING_MARKS or len(set(run)) < len(run)
        for run in _nonspacing_runs(nfd(text))
    )


_DOT_ABOVE = 0x0307


def _hides_dot_above(cp: int) -> bool:
    """ICU's isIllegalCombiningDotLeadCharacter."""
    dotted_looking = _dotted_looking()
    if cp in dotted_looking:
        return True
    # Also the characters whose prototype ends in one of them, such as
    # LATIN CAPITAL LETTER I, whose prototype is l.
    prototype = _prototypes().get(cp)
    return prototype is not None and ord(prototype[-1]) in dotted_looking


def has_hidden_overlay(text: str) -> bool:
    r"""Return whether text puts a dot above where it cannot be seen.

    UTS #39 section 5.4 suggests forbidding a base character with a
    nonspacing mark that looks like the base alone, such as i with U+0307
    COMBINING DOT ABOVE. This is ICU's HIDDEN_OVERLAY check, the only
    implementation of it: a dot above after i, j, l, dotless i or j, a
    Soft_Dotted character, or a character whose prototype ends in one of
    those, with only marks that are not drawn above in between.

    ICU tests the text as written; this tests its NFD, so the result does
    not depend on how the text is encoded. That flags U+0130 LATIN CAPITAL
    LETTER I WITH DOT ABOVE, whose NFD is I and a dot above, as ICU flags I
    with a dot above: I's prototype is l.

    >>> has_hidden_overlay("i\u0307")  # the dot falls on i's own dot
    True
    """
    if text.isascii():
        return False
    decomposed = nfd(text)
    if chr(_DOT_ABOVE) not in decomposed:
        return False
    classes = combining_classes()
    above = classes[_DOT_ABOVE]  # 230
    after_dotted = False
    for c in decomposed:
        cp = ord(c)
        if after_dotted and cp == _DOT_ABOVE:
            return True
        if classes.get(cp, 0) in (0, above):
            after_dotted = _hides_dot_above(cp)
    return False
