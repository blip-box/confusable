"""The conformance corpus: curated attacks plus seeded, generated strings.

The generator draws from pools built out of the pinned Unicode files, so the
corpus covers every script UTS #39 cares about, combining marks in all orders,
invisible and bidirectional controls, emoji sequences, digits from many
systems, and look-alike swaps taken from confusables.txt. A fixed seed makes it
reproducible: regenerating with the same Unicode data yields the same corpus.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from tests.conformance.attacks import ATTACKS

SEED = 39  # UTS #39
STRING_COUNT = 4000
PAIR_COUNT = 2000

# Scripts sampled for letters: the Recommended scripts of UAX #31 Table 5 plus
# a few Limited Use and Excluded ones, so restriction levels see all outcomes.
SCRIPTS = (
    "Latin Cyrillic Greek Armenian Georgian Hebrew Arabic Thaana Devanagari "
    "Bengali Gurmukhi Gujarati Oriya Tamil Telugu Kannada Malayalam Sinhala "
    "Thai Lao Tibetan Myanmar Khmer Ethiopic Han Hiragana Katakana Bopomofo "
    "Hangul Cherokee Coptic Syriac Nko Adlam Runic Canadian_Aboriginal"
).split()

BIDI_CONTROLS = [
    *range(0x202A, 0x202F),  # LRE RLE PDF LRO RLO
    *range(0x2066, 0x206A),  # LRI RLI FSI PDI
    0x200E,  # LRM
    0x200F,  # RLM
    0x061C,  # ALM
]


def _ranges(path: Path) -> Iterator[tuple[range, list[str]]]:
    """Yield (code point range, fields) for each data line of a UCD-style file."""
    with path.open(encoding="utf-8-sig") as lines:
        for line in lines:
            data = line.split("#", 1)[0].strip()
            if not data:
                continue
            first, *rest = (field.strip() for field in data.split(";"))
            start, _, end = first.partition("..")
            yield range(int(start, 16), int(end or start, 16) + 1), rest


def _unicode_data(path: Path) -> tuple[dict[int, str], set[int]]:
    """General_Category of each assigned code point, and the Bidi_Mirrored set."""
    categories: dict[int, str] = {}
    mirrored: set[int] = set()
    range_start: int | None = None
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.split(";")
            cp, name, category = int(fields[0], 16), fields[1], fields[2]
            if fields[9] == "Y":
                mirrored.add(cp)
            if name.endswith(", First>"):
                range_start = cp
            elif name.endswith(", Last>") and range_start is not None:
                for c in range(range_start, cp + 1):
                    categories[c] = category
                range_start = None
            else:
                categories[cp] = category
    return categories, mirrored


def _sequences(path: Path) -> list[str]:
    """Code point sequences from an emoji sequence file's first field."""
    out: list[str] = []
    with path.open(encoding="utf-8-sig") as lines:
        for line in lines:
            data = line.split("#", 1)[0].strip()
            if not data:
                continue
            field = data.split(";")[0].strip()
            if ".." in field:
                start, end = field.split("..")
                out.extend(chr(c) for c in range(int(start, 16), int(end, 16) + 1))
            else:
                out.append("".join(chr(int(cp, 16)) for cp in field.split()))
    return out


class Pools:
    """Characters and sequences to build strings from, by kind."""

    def __init__(self, sources: dict[str, Path]) -> None:
        category, mirrored = _unicode_data(sources["ucd/UnicodeData.txt"])
        # Surrogates are not scalar values, so no string can contain them.
        self.assigned = sorted(c for c, gc in category.items() if gc != "Cs")

        by_script: dict[str, list[int]] = defaultdict(list)
        for cps, (script,) in _ranges(sources["ucd/Scripts.txt"]):
            by_script[script].extend(cps)
        self.allowed = {
            c
            for cps, (status, *_) in _ranges(sources["security/IdentifierStatus.txt"])
            if status == "Allowed"
            for c in cps
        }
        self.letters = {
            script: [c for c in by_script[script] if category.get(c, "Cn")[0] == "L"]
            for script in SCRIPTS
        }
        # Letters inside the General Security Profile, so restriction levels
        # see more than Unrestricted. Excluded scripts have none.
        self.profile_letters = {
            script: [c for c in letters if c in self.allowed] or letters
            for script, letters in self.letters.items()
        }
        self.common = [
            c for c in by_script["Common"] if category.get(c, "Cn")[0] in "PSZ"
        ]
        self.marks = [c for c, gc in category.items() if gc in ("Mn", "Mc", "Me")]
        self.nonspacing = [c for c, gc in category.items() if gc in ("Mn", "Me")]
        self.digits = [c for c, gc in category.items() if gc == "Nd"]
        self.mirrored = sorted(mirrored)

        self.default_ignorable = [
            c
            for cps, (prop, *_) in _ranges(sources["ucd/DerivedCoreProperties.txt"])
            if prop == "Default_Ignorable_Code_Point"
            for c in cps
            if c in category
        ]

        # Look-alikes: for each single-character prototype, the characters
        # that map to it; swapping within a class keeps the skeleton.
        self.lookalikes: dict[str, list[str]] = defaultdict(list)
        self.confusable_sources: list[int] = []
        for cps, (target, *_) in _ranges(sources["security/confusables.txt"]):
            source = cps.start
            self.confusable_sources.append(source)
            prototype = "".join(chr(int(t, 16)) for t in target.split())
            self.lookalikes[prototype].append(chr(source))
        self.lookalike_class: dict[str, list[str]] = {}
        for prototype, members in self.lookalikes.items():
            if len(prototype) == 1:
                group = [prototype, *members]
                for member in group:
                    self.lookalike_class[member] = group

        self.emoji = _sequences(sources["emoji/emoji-sequences.txt"]) + _sequences(
            sources["emoji/emoji-zwj-sequences.txt"]
        )


Style = Callable[[random.Random, Pools], str]


def _pick(rng: random.Random, items: list[int], n: int) -> str:
    return "".join(chr(rng.choice(items)) for _ in range(n))


def _letters(rng: random.Random, p: Pools, script: str, n: int) -> str:
    """Letters of a script, mostly from inside the identifier profile."""
    pool = p.profile_letters if rng.random() < 0.8 else p.letters
    return _pick(rng, pool[script], n)


def single_script(rng: random.Random, p: Pools) -> str:
    script = rng.choice(SCRIPTS)
    text = _letters(rng, p, script, rng.randint(1, 8))
    if rng.random() < 0.3:
        text += _pick(rng, p.digits, 1)
    return text


def mixed_scripts(rng: random.Random, p: Pools) -> str:
    scripts = rng.sample(SCRIPTS, rng.randint(2, 3))
    return "".join(
        _letters(rng, p, rng.choice(scripts), 1) for _ in range(rng.randint(2, 8))
    )


def latin_with(rng: random.Random, p: Pools) -> str:
    """Mix Latin with one other script: the restriction-level boundary cases."""
    other = rng.choice(SCRIPTS)
    parts = [_letters(rng, p, "Latin", rng.randint(1, 4))]
    parts.append(_letters(rng, p, other, rng.randint(1, 4)))
    if rng.random() < 0.3:
        parts.append(_pick(rng, p.common, 1))
    rng.shuffle(parts)
    return "".join(parts)


def cjk(rng: random.Random, p: Pools) -> str:
    pool = ["Han", "Hiragana", "Katakana", "Bopomofo", "Hangul", "Latin"]
    return "".join(
        _letters(rng, p, rng.choice(pool), 1) for _ in range(rng.randint(2, 6))
    )


def lookalike_swap(rng: random.Random, p: Pools) -> str:
    """Swap some letters of an ASCII word for look-alikes."""
    word = "".join(
        rng.choice("abcdeghijklmnopqrstuvwxyz") for _ in range(rng.randint(3, 8))
    )
    out = []
    for ch in word:
        options = p.lookalikes.get(ch)
        out.append(rng.choice(options) if options and rng.random() < 0.4 else ch)
    return "".join(out)


def confusable_sources(rng: random.Random, p: Pools) -> str:
    return _pick(rng, p.confusable_sources, rng.randint(1, 5))


def invisible(rng: random.Random, p: Pools) -> str:
    text = list(_letters(rng, p, rng.choice(SCRIPTS), rng.randint(2, 6)))
    for _ in range(rng.randint(1, 2)):
        text.insert(rng.randint(0, len(text)), chr(rng.choice(p.default_ignorable)))
    return "".join(text)


def bidi(rng: random.Random, p: Pools) -> str:
    """Mix right-to-left letters with neutrals, digits and controls."""
    kinds = [
        lambda: _letters(rng, p, rng.choice(["Hebrew", "Arabic", "Thaana"]), 1),
        lambda: _letters(rng, p, "Latin", 1),
        lambda: _pick(rng, p.mirrored, 1),
        lambda: rng.choice("0123456789"),
        lambda: _pick(rng, p.digits, 1),
        lambda: rng.choice(" .,-+<>/"),
        lambda: _pick(rng, p.marks, 1),
        lambda: chr(rng.choice(BIDI_CONTROLS)),
    ]
    weights = [6, 3, 3, 2, 1, 2, 1, 1]
    return "".join(rng.choices(kinds, weights)[0]() for _ in range(rng.randint(2, 9)))


def combining(rng: random.Random, p: Pools) -> str:
    """Follow base letters with marks in random order, to exercise reordering."""
    out = []
    for _ in range(rng.randint(1, 3)):
        out.append(_letters(rng, p, rng.choice(SCRIPTS), 1))
        out.append(_pick(rng, p.marks, rng.randint(1, 4)))
    return "".join(out)


def repeated_mark(rng: random.Random, p: Pools) -> str:
    """Repeat a nonspacing mark on one base (UTS #39 section 5.4)."""
    mark = chr(rng.choice(p.nonspacing))
    between = _pick(rng, p.nonspacing, 1) if rng.random() < 0.4 else ""
    base = _letters(rng, p, rng.choice(["Latin", "Cyrillic", "Greek", "Arabic"]), 1)
    return base + mark + between + mark


def hidden_overlay(rng: random.Random, p: Pools) -> str:
    """Put a dot above on a letter that already has a dot."""
    base = (
        rng.choice("ij\u0131\u0237\u0456\u0458\u0269")
        if rng.random() < 0.7
        else (_letters(rng, p, "Latin", 1))
    )
    between = _pick(rng, p.nonspacing, 1) if rng.random() < 0.3 else ""
    return _letters(rng, p, "Latin", rng.randint(0, 2)) + base + between + "\u0307"


def emoji(rng: random.Random, p: Pools) -> str:
    parts = [rng.choice(p.emoji) for _ in range(rng.randint(1, 3))]
    if rng.random() < 0.4:
        parts.append(_letters(rng, p, "Latin", 2))
    if rng.random() < 0.2:
        # A stray tag character or two, outside any valid sequence.
        parts.append(chr(rng.choice(range(0xE0020, 0xE0080))) * rng.randint(1, 2))
    rng.shuffle(parts)
    return "".join(parts)


def digits(rng: random.Random, p: Pools) -> str:
    text = _pick(rng, p.digits, rng.randint(1, 4))
    if rng.random() < 0.5:
        text = rng.choice("0123456789") + text
    if rng.random() < 0.3:
        text += _letters(rng, p, rng.choice(SCRIPTS), 2)
    return text


def anything(rng: random.Random, p: Pools) -> str:
    """Use any code points: assigned, unassigned, private use, nonchars."""
    out = []
    for _ in range(rng.randint(1, 6)):
        roll = rng.random()
        if roll < 0.7:
            out.append(chr(rng.choice(p.assigned)))
        elif roll < 0.85:
            c = rng.randrange(0x110000)
            out.append(chr(c if not 0xD800 <= c <= 0xDFFF else 0xFFFD))
        elif roll < 0.95:
            out.append(chr(rng.choice((0xE000, 0xF8FF, 0xF0000, 0x10FFFD))))
        else:
            out.append(chr(rng.choice((0xFFFE, 0xFFFF, 0xFDD0, 0x10FFFF))))
    return "".join(out)


STYLES: tuple[tuple[Style, int], ...] = (
    (single_script, 12),
    (mixed_scripts, 8),
    (latin_with, 10),
    (cjk, 6),
    (lookalike_swap, 12),
    (confusable_sources, 8),
    (invisible, 8),
    (bidi, 12),
    (combining, 8),
    (repeated_mark, 3),
    (hidden_overlay, 2),
    (emoji, 5),
    (digits, 5),
    (anything, 6),
)


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def strings(pools: Pools) -> list[str]:
    """Curated attacks first, then generated strings, without duplicates."""
    rng = random.Random(SEED)
    styles, weights = zip(*STYLES, strict=True)
    generated = (
        rng.choices(styles, weights)[0](rng, pools) for _ in range(STRING_COUNT)
    )
    curated = [a.text for a in ATTACKS]
    curated += [a.confusable_with for a in ATTACKS if a.confusable_with is not None]
    return _unique([*curated, *generated])


def whole_script_spoofs(pools: Pools, rng: random.Random) -> list[tuple[str, str]]:
    """Respell Latin words entirely in one other script's look-alikes."""
    scripts = {c: s for s, letters in pools.letters.items() for c in letters}
    out = []
    for target in ("Cyrillic", "Greek", "Armenian", "Cherokee"):
        spellings = {
            ch: [o for o in group if scripts.get(ord(o)) == target]
            for ch, group in pools.lookalike_class.items()
            if len(ch) == 1 and "a" <= ch <= "z"
        }
        letters = [ch for ch, options in spellings.items() if options]
        for _ in range(40):
            word = "".join(rng.choice(letters) for _ in range(rng.randint(2, 7)))
            out.append((word, "".join(rng.choice(spellings[ch]) for ch in word)))
    return out


def pairs(pools: Pools, corpus: list[str]) -> list[tuple[str, str]]:
    """Curated pairs, whole-script spoofs, look-alike variants, unrelated pairs."""
    rng = random.Random(SEED + 1)
    out = [
        (a.text, a.confusable_with) for a in ATTACKS if a.confusable_with is not None
    ]
    out += whole_script_spoofs(pools, rng)
    while len(out) < PAIR_COUNT:
        text = rng.choice(corpus)
        roll = rng.random()
        if roll < 0.6 and text:
            # Swap one character for a look-alike with the same prototype.
            i = rng.randrange(len(text))
            group = pools.lookalike_class.get(text[i], [])
            options = [o for o in group if o != text[i]]
            if options:
                out.append((text, text[:i] + rng.choice(options) + text[i + 1 :]))
        elif roll < 0.8:
            out.append((text, rng.choice(corpus)))
        else:
            out.append((text, text + rng.choice(corpus)[:1]))
    return out
