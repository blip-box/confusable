"""Read the conformance fixtures that tools/oracles/generate.py writes.

The fixtures are plain text: code point sequences as space-separated hex,
fields separated by tabs, and "#" header lines that describe each file.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path

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


@cache
def strings() -> tuple[StringCase, ...]:
    cases = []
    for row in rows("strings.txt"):
        source, ltr, internal, rtl, normalized, rss, level, checks, zeros, bounds = row
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
                if token == "÷":
                    boundaries.append(len(chars))
                elif token != "×":
                    chars.append(chr(int(token, 16)))
            cases.append(GraphemeCase(number, "".join(chars), tuple(boundaries)))
    return tuple(cases)
