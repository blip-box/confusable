"""Canonical decomposition and composition (NFD, NFC) at the pinned Unicode version.

Python's unicodedata follows the interpreter's Unicode version (13.0 on Python
3.10), so this module uses the generated tables instead.
"""

from __future__ import annotations

from operator import itemgetter

from confusable._data.normalization import (
    CANONICAL_COMBINING_CLASS,
    CANONICAL_COMPOSITION,
    CANONICAL_DECOMPOSITION,
)

# Hangul syllables decompose algorithmically (Unicode section 3.12).
_S_BASE, _L_BASE, _V_BASE, _T_BASE = 0xAC00, 0x1100, 0x1161, 0x11A7
_L_COUNT, _V_COUNT, _T_COUNT = 19, 21, 28
_N_COUNT = _V_COUNT * _T_COUNT
_S_COUNT = _L_COUNT * _N_COUNT

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


def _compose(first: int, second: int) -> int | None:
    """Return the primary composite of two characters, if there is one."""
    l_index = first - _L_BASE
    if 0 <= l_index < _L_COUNT:
        v_index = second - _V_BASE
        return (
            _S_BASE + (l_index * _V_COUNT + v_index) * _T_COUNT
            if 0 <= v_index < _V_COUNT
            else None
        )
    s_index = first - _S_BASE
    if 0 <= s_index < _S_COUNT and s_index % _T_COUNT == 0:
        t_index = second - _T_BASE
        return first + t_index if 0 < t_index < _T_COUNT else None
    return CANONICAL_COMPOSITION.get((first, second))


def nfc(text: str) -> str:
    """Return the canonical composition (NFC) of text."""
    if text.isascii():
        return text
    out: list[str] = []
    starter = -1  # Index in out of the last starter.
    last_class = 0  # Combining class of the last character kept after it.
    for c in nfd(text):
        ccc = CANONICAL_COMBINING_CLASS.get(ord(c), 0)
        # A character composes with the last starter unless a character in
        # between blocks it: one of class 0, or of a class no lower than its own.
        if starter >= 0 and (starter == len(out) - 1 or 0 < last_class < ccc):
            composite = _compose(ord(out[starter]), ord(c))
            if composite is not None:
                out[starter] = chr(composite)
                continue
        if ccc == 0:
            starter = len(out)
        last_class = ccc
        out.append(c)
    return "".join(out)
