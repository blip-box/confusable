"""Extended grapheme clusters (UAX #29 revision 49) and safe truncation.

A grapheme cluster is what a reader takes for one character: a letter with
its accents, a Hangul syllable written in jamo, an emoji with its skin tone
or a whole emoji ZWJ sequence, a flag. Cutting text inside one changes what
it says, so truncation here only cuts between them.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator

from confusable._data import graphemes as _data
from confusable._lookup import Ranges, Runs

_BREAK = Runs(_data.GRAPHEME_CLUSTER_BREAK_RUNS)
_CONJUNCT = Runs(_data.INDIC_CONJUNCT_BREAK_RUNS)
_PICTOGRAPHIC = Ranges(_data.EXTENDED_PICTOGRAPHIC_RANGES)

_CONTROLS = frozenset({"CR", "LF", "Control"})
_HANGUL_AFTER_L = frozenset({"L", "V", "LV", "LVT"})
_JOINS_BEFORE = frozenset({"Extend", "ZWJ", "SpacingMark"})  # GB9, GB9a


class Segment:
    """One grapheme cluster of a string: str(segment) is its text.

    start and end are indexes into the string, as in a slice.
    """

    __slots__ = ("_end", "_start", "_text")

    def __init__(self, text: str, start: int, end: int) -> None:
        self._text = text
        self._start = start
        self._end = end

    @property
    def start(self) -> int:
        """The index of the cluster's first character."""
        return self._start

    @property
    def end(self) -> int:
        """The index just past the cluster's last character."""
        return self._end

    def __str__(self) -> str:
        return self._text[self._start : self._end]

    def __repr__(self) -> str:
        return f"<Segment {self._start}:{self._end}>"


def _boundaries(text: str, start: int, end: int) -> Iterator[int]:
    """Yield the grapheme cluster boundaries of text[start:end] after start.

    The rules are those of UAX #29 section 3.1.1 for extended grapheme
    clusters, applied to text[start:end] as a string of its own.
    """
    if start >= end:
        return
    if text.isascii():  # only GB3, CR LF, joins ASCII characters
        for i in range(start + 1, end):
            if text[i - 1 : i + 1] != "\r\n":
                yield i
        yield end
        return
    c = text[start]
    before = _BREAK[ord(c)]
    # State for the rules that look further back than one character.
    odd_regional_indicators = before == "Regional_Indicator"  # GB12, GB13
    after_linker = _CONJUNCT[ord(c)] == "Linker"  # GB9c: Linker Extend*
    after_pictographic = ord(c) in _PICTOGRAPHIC  # GB11: ExtPict Extend*
    after_emoji_zwj = False  # GB11: ExtPict Extend* ZWJ
    for i in range(start + 1, end):
        c = text[i]
        cp = ord(c)
        current = _BREAK[cp]
        conjunct = _CONJUNCT[cp]
        pictographic = cp in _PICTOGRAPHIC
        if before == "CR" and current == "LF":  # GB3
            joined = True
        elif before in _CONTROLS or current in _CONTROLS:  # GB4, GB5
            joined = False
        else:
            # The remaining rules all join, except GB999, which breaks.
            joined = (
                (before == "L" and current in _HANGUL_AFTER_L)  # GB6
                or (before in ("LV", "V") and current in ("V", "T"))  # GB7
                or (before in ("LVT", "T") and current == "T")  # GB8
                or current in _JOINS_BEFORE  # GB9, GB9a
                or before == "Prepend"  # GB9b
                or (after_linker and conjunct == "Consonant")  # GB9c
                or (after_emoji_zwj and pictographic)  # GB11
                or (  # GB12, GB13
                    current == "Regional_Indicator" and odd_regional_indicators
                )
            )
        if not joined:
            yield i
        odd_regional_indicators = current == "Regional_Indicator" and not (
            before == "Regional_Indicator" and odd_regional_indicators
        )
        if conjunct == "Linker":
            after_linker = True
        elif conjunct != "Extend":
            after_linker = False
        after_emoji_zwj = current == "ZWJ" and after_pictographic
        after_pictographic = pictographic or (
            after_pictographic and current == "Extend"
        )
        before = current
    yield end


def iter_graphemes(
    text: str, start: int = 0, end: int = sys.maxsize, /
) -> Iterator[Segment]:
    r"""Iterate over the extended grapheme clusters of text, as Segments.

    The same as Python 3.15's unicodedata.iter_graphemes, on every Python
    version and at confusable's Unicode version (see unicode_version) rather
    than the interpreter's. start and end select text[start:end], as in a
    slice, which is segmented as a string of its own.

    >>> list(iter_graphemes("e\u0301\U0001f1fa\U0001f1f8!"))  # e, ACUTE, a flag, !
    [<Segment 0:2>, <Segment 2:4>, <Segment 4:5>]
    >>> [str(g) for g in iter_graphemes("abc")]
    ['a', 'b', 'c']
    """
    if not isinstance(text, str):
        raise TypeError(
            f"iter_graphemes() argument 1 must be str, not {type(text).__name__}"
        )
    # Checked here, not when iteration starts, as for unicodedata's.
    start, end, _ = slice(start, end).indices(len(text))
    return _segments(text, start, end)


def _segments(text: str, start: int, end: int) -> Iterator[Segment]:
    previous = start
    for boundary in _boundaries(text, start, end):
        yield Segment(text, previous, boundary)
        previous = boundary


def _utf8_length(c: str) -> int:
    cp = ord(c)
    return 1 if cp < 0x80 else 2 if cp < 0x800 else 3 if cp < 0x10000 else 4


def truncate(
    text: str,
    max_graphemes: int | None = None,
    *,
    max_code_points: int | None = None,
    max_utf8_bytes: int | None = None,
    max_utf16_units: int | None = None,
) -> str:
    r"""Return the longest start of text that keeps within every given limit.

    The result is always whole grapheme clusters, so truncation never splits
    a character from its accents, an emoji sequence or a flag. Limits:

    - max_graphemes: user-perceived characters.
    - max_code_points: len() of a Python string, and what PostgreSQL and
      MySQL count for a VARCHAR(n) column.
    - max_utf8_bytes: the size encoded as UTF-8.
    - max_utf16_units: the length in UTF-16 code units, as JavaScript, Java
      and C# count it.

    A grapheme cluster has no size limit (UAX #29 section 3), so a grapheme
    limit alone does not bound storage: pair it with one of the others. A
    first cluster that is already too large gives the empty string.

    >>> truncate("cafe\u0301 cr\u00e8me", 4) == "cafe\u0301"  # keeps the accent
    True
    >>> flags = "\U0001f1fa\U0001f1f8\U0001f1ec\U0001f1e7"  # two flags
    >>> truncate(flags, max_utf16_units=6) == flags[:2]
    True
    """
    limits = (max_graphemes, max_code_points, max_utf8_bytes, max_utf16_units)
    if all(limit is None for limit in limits):
        raise TypeError("truncate() needs at least one limit")
    if any(limit is not None and limit < 0 for limit in limits):
        raise ValueError("limits must not be negative")
    # A character is at most one grapheme, 4 UTF-8 bytes or 2 UTF-16 units.
    n = len(text)
    if (
        (max_graphemes is None or n <= max_graphemes)
        and (max_code_points is None or n <= max_code_points)
        and (max_utf8_bytes is None or 4 * n <= max_utf8_bytes)
        and (max_utf16_units is None or 2 * n <= max_utf16_units)
    ):
        return text
    graphemes = code_points = utf8 = utf16 = 0
    for segment in iter_graphemes(text):
        cluster = str(segment)
        graphemes += 1
        code_points += len(cluster)
        if max_utf8_bytes is not None:
            utf8 += sum(_utf8_length(c) for c in cluster)
        if max_utf16_units is not None:
            utf16 += len(cluster) + sum(1 for c in cluster if ord(c) > 0xFFFF)
        if (
            (max_graphemes is not None and graphemes > max_graphemes)
            or (max_code_points is not None and code_points > max_code_points)
            or (max_utf8_bytes is not None and utf8 > max_utf8_bytes)
            or (max_utf16_units is not None and utf16 > max_utf16_units)
        ):
            return text[: segment.start]
    return text
