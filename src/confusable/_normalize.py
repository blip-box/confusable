"""Canonical decomposition (NFD) at the pinned Unicode version.

Python's unicodedata follows the interpreter's Unicode version (13.0 on Python
3.10), so this module uses the generated tables instead.
"""

from __future__ import annotations

from operator import itemgetter

from confusable._data.normalization import (
    CANONICAL_COMBINING_CLASS,
    CANONICAL_DECOMPOSITION,
)

# Hangul syllables decompose algorithmically (Unicode section 3.12).
_S_BASE, _L_BASE, _V_BASE, _T_BASE = 0xAC00, 0x1100, 0x1161, 0x11A7
_T_COUNT = 28
_N_COUNT = 21 * _T_COUNT
_S_COUNT = 19 * _N_COUNT

_by_class = itemgetter(0)


def _decompose(c: str) -> str:
    s_index = ord(c) - _S_BASE
    if 0 <= s_index < _S_COUNT:
        lead = chr(_L_BASE + s_index // _N_COUNT)
        vowel = chr(_V_BASE + (s_index % _N_COUNT) // _T_COUNT)
        t_index = s_index % _T_COUNT
        return lead + vowel + (chr(_T_BASE + t_index) if t_index else "")
    return CANONICAL_DECOMPOSITION.get(ord(c), c)


def nfd(text: str) -> str:
    """Return the canonical decomposition (NFD) of text."""
    if text.isascii():
        return text
    out: list[str] = []
    marks: list[tuple[int, str]] = []
    for c in "".join(map(_decompose, text)):
        ccc = CANONICAL_COMBINING_CLASS.get(ord(c), 0)
        if ccc:
            marks.append((ccc, c))
            continue
        if marks:
            # Canonical ordering: a stable sort of each run of marks by class.
            out.extend(mark for _, mark in sorted(marks, key=_by_class))
            marks.clear()
        out.append(c)
    out.extend(mark for _, mark in sorted(marks, key=_by_class))
    return "".join(out)
