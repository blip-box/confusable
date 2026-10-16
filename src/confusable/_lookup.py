"""Lookups in the generated tables (see tools/generate_tables.py)."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence


class Runs:
    """An enumerated property stored as (first code point, value) runs."""

    __slots__ = ("_starts", "_values")

    def __init__(self, runs: Sequence[tuple[int, str]]) -> None:
        self._starts = tuple(first for first, _ in runs)
        self._values = tuple(value for _, value in runs)

    def __getitem__(self, cp: int) -> str:
        return self._values[bisect_right(self._starts, cp) - 1]


class Ranges:
    """A set of code points stored as sorted (first, last) ranges."""

    __slots__ = ("_firsts", "_lasts")

    def __init__(self, ranges: Sequence[tuple[int, int]]) -> None:
        self._firsts = tuple(first for first, _ in ranges)
        self._lasts = tuple(last for _, last in ranges)

    def __contains__(self, cp: int) -> bool:
        i = bisect_right(self._firsts, cp) - 1
        return i >= 0 and cp <= self._lasts[i]
