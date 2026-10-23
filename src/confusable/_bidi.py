"""The Unicode Bidirectional Algorithm (UAX #9 revision 52, Unicode 18.0).

UTS #39 defines skeleton(X) as bidiSkeleton(LTR, X), which puts X into display
order before mapping look-alikes: rules P1-P3, X1-X10, W1-W7, N0-N2, I1-I2 and
L1-L2 of UAX #9, then L3 (combining marks follow their base) and L4 (mirrored
glyphs). This module implements all of them for the skeleton; it is not a
text-rendering API.

Rule X9 removes embedding controls and boundary neutrals (BN) from the
algorithm, and UAX #9 does not say where they go in display order, but
bidiSkeleton keeps the ones that are not Default_Ignorable (C0 and C1 controls,
for example). display() places them the way ICU does, so skeletons agree with
ICU's: at the level of the character that follows them, or at the paragraph
level when they trail a line or precede a separator.

Text reorders only within a paragraph (UAX #9 section 2), and CR LF counts as
one paragraph separator. ICU's bidiSkeleton reorders several paragraphs as one
line; the conformance oracle patches that.

UTS #39 notes a fast path: in a left-to-right paragraph, text without R or AL
characters keeps its order. That is incomplete. Only R, AL, AN, RLE, RLO and
RLI can bring text to an odd level, so all six must be absent: RLO reverses
Latin letters, and a neutral between two AN digits resolves to R.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from confusable._data import bidi as _data
from confusable._lookup import Ranges, Runs

Direction = Literal["LTR", "RTL", "auto"]

MAX_DEPTH = 125
_BRACKET_STACK_SIZE = 63

_BIDI_CLASS = Runs(_data.BIDI_CLASS_RUNS)
_COMBINING_MARKS = Ranges(_data.COMBINING_MARK_RANGES)

_ISOLATE_INITIATORS = frozenset({"LRI", "RLI", "FSI"})
_EMBEDDING_INITIATORS = frozenset({"LRE", "RLE", "LRO", "RLO"})
_REMOVED_BY_X9 = frozenset({"LRE", "RLE", "LRO", "RLO", "PDF", "BN"})
# Neutral and isolate formatting types (NI), as rules N1 and N2 use them.
_NEUTRALS = frozenset({"B", "S", "WS", "ON", "LRI", "RLI", "FSI", "PDI"})
# Types that rule L1 resets when they trail a line or precede a separator.
_TRAILING = frozenset({"WS", "LRI", "RLI", "FSI", "PDI"})


def bidi_class(cp: int) -> str:
    """Return the Bidi_Class of a code point, as its short name."""
    return _BIDI_CLASS[cp]


def _odd_above(level: int) -> int:
    """Return the least odd level greater than level."""
    return (level + 1) | 1


def _even_above(level: int) -> int:
    """Return the least even level greater than level."""
    return (level + 2) & ~1


def _matching_pdis(types: Sequence[str]) -> dict[int, int]:
    """BD9: the matching PDI of each isolate initiator that has one."""
    matches = {}
    open_initiators: list[int] = []
    for i, t in enumerate(types):
        if t in _ISOLATE_INITIATORS:
            open_initiators.append(i)
        elif t == "PDI" and open_initiators:
            matches[open_initiators.pop()] = i
    return matches


def _first_strong(
    types: Sequence[str], start: int, end: int, matches: dict[int, int]
) -> int | None:
    """P2 and P3: level 1 or 0 from the first strong type, or None if none."""
    i = start
    while i < end:
        t = types[i]
        if t == "L":
            return 0
        if t in ("R", "AL"):
            return 1
        if t in _ISOLATE_INITIATORS:
            i = matches.get(i, end)
        i += 1
    return None


@dataclass
class Paragraph:
    """One resolved paragraph of the input (rule P1)."""

    start: int
    level: int
    # Resolved levels after L1; None for characters that rule X9 removes.
    levels: list[int | None]
    # Levels used for display, with the X9-removed characters placed too.
    display_levels: list[int]


def resolve(
    types: Sequence[str],
    direction: Direction,
    code_points: Sequence[int] | None = None,
) -> list[Paragraph]:
    """Resolve embedding levels for a sequence of Bidi_Class values.

    code_points gives the characters, for bracket pairs (rule N0); without
    it no characters pair as brackets, as BidiTest.txt assumes.
    """
    paragraphs = []
    start = 0
    for end in range(len(types)):
        if types[end] != "B":
            continue
        # CR LF is a single newline function, so one paragraph separator.
        if (
            code_points is not None
            and code_points[end] == 0x0D
            and end + 1 < len(types)
            and code_points[end + 1] == 0x0A
        ):
            continue
        paragraphs.append(_paragraph(types, code_points, start, end + 1, direction))
        start = end + 1
    if start < len(types) or not types:
        paragraphs.append(_paragraph(types, code_points, start, len(types), direction))
    return paragraphs


def _paragraph(
    all_types: Sequence[str],
    all_code_points: Sequence[int] | None,
    start: int,
    end: int,
    direction: Direction,
) -> Paragraph:
    types = all_types[start:end]
    code_points = all_code_points[start:end] if all_code_points is not None else None
    matches = _matching_pdis(types)
    if direction == "auto":
        level = _first_strong(types, 0, len(types), matches) or 0
    else:
        level = 0 if direction == "LTR" else 1

    explicit, current = _explicit_levels(types, level, matches)
    kept = [i for i, t in enumerate(types) if t not in _REMOVED_BY_X9]
    resolved: list[int | None] = [None] * len(types)
    for i in kept:
        resolved[i] = explicit[i]

    for sequence, sos, eos in _isolating_run_sequences(
        types, explicit, kept, matches, level
    ):
        _resolve_sequence(
            sequence, sos, eos, explicit[sequence[0]], current, code_points, resolved
        )

    # L1, on the original types and ignoring the characters X9 removed.
    trailing = True
    for i in reversed(kept):
        if types[i] in ("S", "B"):
            resolved[i] = level
            trailing = True
        elif types[i] in _TRAILING:
            if trailing:
                resolved[i] = level
        else:
            trailing = False

    # Place the removed characters as ICU does (see the module docstring).
    display: list[int] = [level] * len(types)
    trailing = True
    following = level
    for i in reversed(range(len(types))):
        value = resolved[i]
        if value is None:
            display[i] = level if trailing else following
        else:
            display[i] = value
            if types[i] in ("S", "B"):
                trailing = True
            elif types[i] not in _TRAILING:
                trailing = False
        following = display[i]
    return Paragraph(start, level, resolved, display)


def _explicit_levels(
    types: Sequence[str], paragraph_level: int, matches: dict[int, int]
) -> tuple[list[int], list[str]]:
    """X1-X8: explicit embedding levels and the types after overrides."""
    levels = [paragraph_level] * len(types)
    current = list(types)
    # Entries: (embedding level, override type or "", isolate status).
    stack: list[tuple[int, str, bool]] = [(paragraph_level, "", False)]
    overflow_isolates = overflow_embeddings = valid_isolates = 0

    for i, t in enumerate(types):
        top_level, override, _ = stack[-1]
        if t in _EMBEDDING_INITIATORS:
            # Retained for display at the level outside the embedding.
            levels[i] = top_level
            new = _odd_above(top_level) if t[0] == "R" else _even_above(top_level)
            if new <= MAX_DEPTH and overflow_isolates == 0 and overflow_embeddings == 0:
                stack.append((new, {"RLO": "R", "LRO": "L"}.get(t, ""), False))
            elif overflow_isolates == 0:
                overflow_embeddings += 1
        elif t in _ISOLATE_INITIATORS:
            levels[i] = top_level
            if override:
                current[i] = override
            if t == "FSI":
                rtl = (
                    _first_strong(types, i + 1, matches.get(i, len(types)), matches)
                    == 1
                )
            else:
                rtl = t == "RLI"
            new = _odd_above(top_level) if rtl else _even_above(top_level)
            if new <= MAX_DEPTH and overflow_isolates == 0 and overflow_embeddings == 0:
                valid_isolates += 1
                stack.append((new, "", True))
            else:
                overflow_isolates += 1
        elif t == "PDI":
            if overflow_isolates > 0:
                overflow_isolates -= 1
            elif valid_isolates > 0:
                overflow_embeddings = 0
                while not stack[-1][2]:
                    stack.pop()
                stack.pop()
                valid_isolates -= 1
            top_level, override, _ = stack[-1]
            levels[i] = top_level
            if override:
                current[i] = override
        elif t == "PDF":
            if overflow_isolates > 0:
                pass
            elif overflow_embeddings > 0:
                overflow_embeddings -= 1
            elif not stack[-1][2] and len(stack) >= 2:
                stack.pop()
            levels[i] = stack[-1][0]
        elif t == "B":
            levels[i] = paragraph_level
        else:
            # X6, extended to BN for display; BN keeps its type.
            levels[i] = top_level
            if override and t != "BN":
                current[i] = override
    return levels, current


def _isolating_run_sequences(
    types: Sequence[str],
    levels: Sequence[int],
    kept: list[int],
    matches: dict[int, int],
    paragraph_level: int,
) -> list[tuple[list[int], str, str]]:
    """X10 and BD13: isolating run sequences, each with its sos and eos."""
    runs: list[list[int]] = []
    for i in kept:
        if runs and levels[runs[-1][-1]] == levels[i]:
            runs[-1].append(i)
        else:
            runs.append([i])
    run_of = {run[0]: n for n, run in enumerate(runs)}
    matched_pdis = set(matches.values())
    position = {i: n for n, i in enumerate(kept)}

    sequences = []
    for run in runs:
        if types[run[0]] == "PDI" and run[0] in matched_pdis:
            continue
        sequence = list(run)
        while types[sequence[-1]] in _ISOLATE_INITIATORS and sequence[-1] in matches:
            pdi = matches[sequence[-1]]
            if pdi not in run_of:
                break
            sequence.extend(runs[run_of[pdi]])

        first, last = sequence[0], sequence[-1]
        before = position[first] - 1
        before_level = levels[kept[before]] if before >= 0 else paragraph_level
        after = position[last] + 1
        if after < len(kept) and types[last] not in _ISOLATE_INITIATORS:
            after_level = levels[kept[after]]
        else:
            after_level = paragraph_level
        sos = "R" if max(levels[first], before_level) % 2 else "L"
        eos = "R" if max(levels[last], after_level) % 2 else "L"
        sequences.append((sequence, sos, eos))
    return sequences


def _strong(t: str) -> str:
    """Return the direction of a resolved type, with EN and AN counting as R."""
    if t == "L":
        return "L"
    if t in ("R", "EN", "AN"):
        return "R"
    return ""


def _resolve_sequence(
    sequence: list[int],
    sos: str,
    eos: str,
    level: int,
    current: Sequence[str],
    code_points: Sequence[int] | None,
    resolved: list[int | None],
) -> None:
    """W1-W7, N0-N2 and I1-I2 on one isolating run sequence."""
    t = [current[i] for i in sequence]
    before_w1 = list(t)
    n = len(t)

    # W1: nonspacing marks take the type of what precedes them.
    previous = sos
    for k in range(n):
        if t[k] == "NSM":
            t[k] = (
                "ON"
                if previous in _ISOLATE_INITIATORS or previous == "PDI"
                else previous
            )
        previous = t[k]
    # W2: European numbers after Arabic letters are Arabic numbers.
    last_strong = sos
    for k in range(n):
        if t[k] in ("L", "R", "AL"):
            last_strong = t[k]
        elif t[k] == "EN" and last_strong == "AL":
            t[k] = "AN"
    # W3
    t = ["R" if x == "AL" else x for x in t]
    # W4: a single separator between two numbers of the same type.
    for k in range(1, n - 1):
        if t[k] == "ES" and t[k - 1] == "EN" and t[k + 1] == "EN":
            t[k] = "EN"
        elif t[k] == "CS" and t[k - 1] == t[k + 1] and t[k - 1] in ("EN", "AN"):
            t[k] = t[k - 1]
    # W5: terminators next to European numbers.
    k = 0
    while k < n:
        if t[k] != "ET":
            k += 1
            continue
        j = k
        while j < n and t[j] == "ET":
            j += 1
        if (k > 0 and t[k - 1] == "EN") or (j < n and t[j] == "EN"):
            t[k:j] = ["EN"] * (j - k)
        k = j
    # W6
    t = ["ON" if x in ("ES", "ET", "CS") else x for x in t]
    # W7: European numbers after left-to-right text are left-to-right.
    last_strong = sos
    for k in range(n):
        if t[k] in ("L", "R"):
            last_strong = t[k]
        elif t[k] == "EN" and last_strong == "L":
            t[k] = "L"

    embedding = "R" if level % 2 else "L"
    if code_points is not None:
        _resolve_brackets(
            t, before_w1, [code_points[i] for i in sequence], sos, embedding
        )

    # N1 and N2: runs of neutrals.
    k = 0
    while k < n:
        if t[k] not in _NEUTRALS:
            k += 1
            continue
        j = k
        while j < n and t[j] in _NEUTRALS:
            j += 1
        before = sos if k == 0 else _strong(t[k - 1])
        after = eos if j == n else _strong(t[j])
        t[k:j] = [before if before == after else embedding] * (j - k)
        k = j

    # I1 and I2.
    for k, i in enumerate(sequence):
        if level % 2 == 0:
            if t[k] == "R":
                resolved[i] = level + 1
            elif t[k] in ("AN", "EN"):
                resolved[i] = level + 2
            else:
                resolved[i] = level
        elif t[k] in ("L", "EN", "AN"):
            resolved[i] = level + 1
        else:
            resolved[i] = level


def _canonical_bracket(cp: int) -> int:
    return _data.BRACKET_CANONICAL.get(cp, cp)


def _bracket_pairs(t: list[str], code_points: list[int]) -> list[tuple[int, int]]:
    """BD16: bracket pairs in an isolating run sequence, by opening position."""
    stack: list[tuple[int, int]] = []
    pairs = []
    for k, cp in enumerate(code_points):
        info = _data.BIDI_BRACKETS.get(cp)
        if info is None or t[k] != "ON":
            continue
        pair, kind = info
        if kind == "o":
            if len(stack) == _BRACKET_STACK_SIZE:
                return []
            stack.append((_canonical_bracket(pair), k))
            continue
        closing = _canonical_bracket(cp)
        for depth in range(len(stack) - 1, -1, -1):
            if stack[depth][0] == closing:
                pairs.append((stack[depth][1], k))
                del stack[depth:]
                break
    return sorted(pairs)


def _resolve_brackets(
    t: list[str], before_w1: list[str], code_points: list[int], sos: str, embedding: str
) -> None:
    """N0: bracket pairs take the direction of their content or context."""
    for opening, closing in _bracket_pairs(t, code_points):
        inside = {_strong(x) for x in t[opening + 1 : closing]} - {""}
        if not inside:
            continue
        if embedding in inside:
            direction = embedding
        else:
            context = next((s for s in map(_strong, reversed(t[:opening])) if s), sos)
            direction = context
        for bracket in (opening, closing):
            t[bracket] = direction
            k = bracket + 1
            while k < len(t) and before_w1[k] == "NSM":
                t[k] = direction
                k += 1


def _visual_order(levels: Sequence[int]) -> list[int]:
    """L2: the visual order, left to right, of items with these levels."""
    order = list(range(len(levels)))
    if not order:
        return order
    current = list(levels)
    for level in range(max(current), (min(current) | 1) - 1, -1):
        k = 0
        while k < len(order):
            if current[k] < level:
                k += 1
                continue
            j = k
            while j < len(order) and current[j] >= level:
                j += 1
            order[k:j] = order[k:j][::-1]
            current[k:j] = current[k:j][::-1]
            k = j
    return order


def levels_and_order(
    types: Sequence[str],
    direction: Direction,
    code_points: Sequence[int] | None = None,
) -> tuple[int, list[int | None], list[int]]:
    """Resolve levels and visual order, as the UCD bidi test files state them.

    Returns the first paragraph's level, the level of every character (None
    for those X9 removes), and the visual order of the remaining characters
    as indices into the input, left to right, paragraph by paragraph.
    """
    paragraphs = resolve(types, direction, code_points)
    levels: list[int | None] = []
    order: list[int] = []
    for paragraph in paragraphs:
        levels.extend(paragraph.levels)
        kept = [
            (k, value) for k, value in enumerate(paragraph.levels) if value is not None
        ]
        visual = _visual_order([value for _, value in kept])
        order.extend(paragraph.start + kept[n][0] for n in visual)
    return paragraphs[0].level, levels, order


def display(text: str, direction: Direction) -> str:
    """Text in display order with L3 and L4 applied: UTS #39's R''.

    The input to internalSkeleton in bidiSkeleton(direction, text).
    """
    code_points = [ord(c) for c in text]
    types = [bidi_class(cp) for cp in code_points]
    out: list[str] = []
    for paragraph in resolve(types, direction, code_points):
        start = paragraph.start
        levels = paragraph.display_levels
        # Level runs in logical order, reordered as units (L2).
        runs: list[tuple[int, int]] = []
        for k in range(len(levels)):
            if runs and levels[runs[-1][0]] == levels[k]:
                runs[-1] = (runs[-1][0], k + 1)
            else:
                runs.append((k, k + 1))
        run_levels = [levels[first] for first, _ in runs]
        for n in _visual_order(run_levels):
            first, last = runs[n]
            if run_levels[n] % 2 == 0:
                out.extend(text[start + first : start + last])
                continue
            # A right-to-left run: reverse it, keeping each base character
            # before its combining marks (L3) and mirroring the base (L4).
            j = last
            while j > first:
                k = j - 1
                while k > first and code_points[start + k] in _COMBINING_MARKS:
                    k -= 1
                base = code_points[start + k]
                out.append(chr(_data.BIDI_MIRRORING_GLYPH.get(base, base)))
                out.extend(text[start + k + 1 : start + j])
                j = k
    return "".join(out)
