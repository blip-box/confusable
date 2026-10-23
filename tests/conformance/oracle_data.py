"""Read the conformance fixtures that tools/oracles/generate.py writes.

The fixtures are plain text: code point sequences as space-separated hex,
fields separated by tabs, and "#" header lines that describe each file.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

FIXTURES = Path(__file__).parent / "fixtures"
UNICODE_VERSION = "18.0.0"

# Every Unicode scalar value: all code points except surrogates.
SCALAR_VALUES = (*range(0xD800), *range(0xE000, 0x110000))


def text(field: str) -> str:
    """Decode a space-separated hex code point sequence."""
    return "".join(chr(int(token, 16)) for token in field.split())


def hex_seq(value: str) -> str:
    return " ".join(f"{ord(c):04X}" for c in value)


def header(name: str) -> list[str]:
    with (FIXTURES / name).open(encoding="utf-8") as lines:
        return [line.rstrip("\n") for line in lines if line.startswith("#")]


def rows(name: str) -> Iterator[list[str]]:
    with (FIXTURES / name).open(encoding="utf-8") as lines:
        for line in lines:
            if not line.startswith("#"):
                yield line.rstrip("\n").split("\t")


def _codepoint_map(name: str) -> dict[str, str]:
    return {text(cp): text(value) for cp, value in rows(name)}


@cache
def skeletons() -> dict[str, str]:
    """skeleton(c) for the code points that are not their own skeleton."""
    return _codepoint_map("skeleton.txt")


@cache
def rtl_skeletons() -> dict[str, str]:
    """bidiSkeleton(RTL, c) where it differs from skeleton(c)."""
    return _codepoint_map("skeleton-rtl.txt")


@cache
def nfd() -> dict[str, str]:
    """NFD(c) for the code points that NFD changes."""
    return _codepoint_map("nfd.txt")


@dataclass(frozen=True)
class Property:
    """One property from properties.txt: a default and explicit ranges."""

    name: str
    default: str
    values: dict[int, str]

    def __call__(self, cp: int) -> str:
        return self.values.get(cp, self.default)


@cache
def properties() -> dict[str, Property]:
    out: dict[str, Property] = {}
    current: Property | None = None
    with (FIXTURES / "properties.txt").open(encoding="utf-8") as lines:
        for line in lines:
            line = line.rstrip("\n")
            if line.startswith("## "):
                name, default = line[3:].split("\t")
                current = Property(name, default.removeprefix("default="), {})
                out[name] = current
            elif line and not line.startswith("#"):
                assert current is not None
                span, value = line.split("\t")
                start, _, end = span.partition("..")
                for cp in range(int(start, 16), int(end or start, 16) + 1):
                    current.values[cp] = value
    return out


@dataclass(frozen=True)
class StringCase:
    """Expected results for one corpus string (a row of strings.txt)."""

    text: str
    skeleton: str
    internal_skeleton: str
    rtl_skeleton: str
    nfd: str
    # Sorted ISO 15924 codes separated by spaces, "ALL", or "" (empty set).
    resolved_script_set: str
    restriction_level: str
    failed_checks: frozenset[str]
    decimal_zeros: frozenset[str]
    grapheme_boundaries: tuple[int, ...]
    # R'' of bidiSkeleton: display order with UAX #9 L3 and L4 applied.
    display_ltr: str
    display_rtl: str


@cache
def strings() -> tuple[StringCase, ...]:
    cases = []
    for row in rows("strings.txt"):
        source, ltr, internal, rtl, normalized, rss, level, checks, zeros, bounds = row[
            :10
        ]
        display_ltr, display_rtl = row[10:]
        cases.append(
            StringCase(
                text=text(source),
                skeleton=text(ltr),
                internal_skeleton=text(ltr if internal == "=" else internal),
                rtl_skeleton=text(ltr if rtl == "=" else rtl),
                nfd=text(source if normalized == "=" else normalized),
                resolved_script_set=rss,
                restriction_level=level,
                failed_checks=frozenset(checks.split()),
                decimal_zeros=frozenset(text(zeros)),
                grapheme_boundaries=tuple(int(b) for b in bounds.split()),
                display_ltr=text(source if display_ltr == "=" else display_ltr),
                display_rtl=text(source if display_rtl == "=" else display_rtl),
            )
        )
    return tuple(cases)


@dataclass(frozen=True)
class PairCase:
    """Expected confusable classes for one pair (a row of pairs.txt)."""

    a: str
    b: str
    # Subsets of {"SINGLE_SCRIPT", "MIXED_SCRIPT", "WHOLE_SCRIPT"}; empty
    # when the pair is not confusable.
    confusable: frozenset[str]
    internal: frozenset[str]
    rtl: frozenset[str]


@cache
def pairs() -> tuple[PairCase, ...]:
    cases = []
    for a, b, ltr, internal, rtl in rows("pairs.txt"):
        cases.append(
            PairCase(
                a=text(a),
                b=text(b),
                confusable=frozenset(ltr.split()),
                internal=frozenset((ltr if internal == "=" else internal).split()),
                rtl=frozenset((ltr if rtl == "=" else rtl).split()),
            )
        )
    return tuple(cases)


def rgi_emoji_sequences() -> tuple[tuple[str, str], ...]:
    """Every RGI emoji sequence and its type, from emoji-sequences.txt."""
    return tuple((text(fields[0]), fields[1]) for fields in rows("emoji-sequences.txt"))


@dataclass(frozen=True)
class GraphemeCase:
    """One line of Unicode's GraphemeBreakTest.txt."""

    line: int
    text: str
    boundaries: tuple[int, ...]


@cache
def grapheme_break_tests() -> tuple[GraphemeCase, ...]:
    cases = []
    path = FIXTURES / "GraphemeBreakTest.txt"
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, 1):
            data = line.split("#", 1)[0].split()
            if not data:
                continue
            chars: list[str] = []
            boundaries = []
            for token in data:
                if token == "\u00f7":
                    boundaries.append(len(chars))
                elif token != "\u00d7":
                    chars.append(chr(int(token, 16)))
            cases.append(GraphemeCase(number, "".join(chars), tuple(boundaries)))
    return tuple(cases)


BidiDirection = Literal["LTR", "RTL", "auto"]
BIDI_DIRECTIONS: dict[str, BidiDirection] = {"0": "LTR", "1": "RTL", "2": "auto"}


@dataclass(frozen=True)
class BidiCase:
    """One expected result from Unicode's bidi conformance tests.

    Levels are None for the characters rule X9 removes; order lists the
    others by index, left to right.
    """

    line: int
    direction: BidiDirection
    levels: tuple[int | None, ...]
    order: tuple[int, ...]
    # BidiCharacterTest.txt only: the text and the paragraph level.
    text: str = ""
    paragraph_level: int = 0
    # BidiTest.txt only: Bidi_Class values instead of text.
    classes: tuple[str, ...] = ()


def _gzip_lines(name: str) -> Iterator[tuple[int, str]]:
    with gzip.open(FIXTURES / name, "rt", encoding="utf-8") as lines:
        for number, line in enumerate(lines, 1):
            yield number, line.rstrip("\n")


def _levels(field: str) -> tuple[int | None, ...]:
    return tuple(None if x == "x" else int(x) for x in field.split())


@cache
def bidi_character_tests() -> tuple[BidiCase, ...]:
    cases = []
    for number, line in _gzip_lines("BidiCharacterTest.txt.gz"):
        if not line or line.startswith("#"):
            continue
        source, direction, paragraph, levels, order = line.split(";")
        cases.append(
            BidiCase(
                line=number,
                direction=BIDI_DIRECTIONS[direction],
                levels=_levels(levels),
                order=tuple(int(x) for x in order.split()),
                text=text(source),
                paragraph_level=int(paragraph),
            )
        )
    return tuple(cases)


@cache
def bidi_tests() -> tuple[BidiCase, ...]:
    """BidiTest.txt, one case per data line and paragraph direction."""
    cases = []
    levels: tuple[int | None, ...] = ()
    order: tuple[int, ...] = ()
    for number, line in _gzip_lines("BidiTest.txt.gz"):
        data = line.split("#", 1)[0].strip()
        if data.startswith("@Levels:"):
            levels = _levels(data.removeprefix("@Levels:"))
        elif data.startswith("@Reorder:"):
            order = tuple(int(x) for x in data.removeprefix("@Reorder:").split())
        elif data and not data.startswith("@"):
            classes, bitset = data.split(";")
            directions: tuple[tuple[int, BidiDirection], ...] = (
                (1, "auto"),
                (2, "LTR"),
                (4, "RTL"),
            )
            for bit, direction in directions:
                if int(bitset, 16) & bit:
                    cases.append(
                        BidiCase(
                            number,
                            direction,
                            levels,
                            order,
                            classes=tuple(classes.split()),
                        )
                    )
    return tuple(cases)


@dataclass(frozen=True)
class NormalizationCase:
    """One line of Unicode's NormalizationTest.txt: columns c1 to c5."""

    line: int
    columns: tuple[str, str, str, str, str]


@cache
def normalization_tests() -> tuple[NormalizationCase, ...]:
    cases = []
    for number, line in _gzip_lines("NormalizationTest.txt.gz"):
        if not line or line.startswith(("#", "@")):
            continue
        c1, c2, c3, c4, c5 = (text(field) for field in line.split(";")[:5])
        cases.append(NormalizationCase(number, (c1, c2, c3, c4, c5)))
    return tuple(cases)
