"""Generate the package's Unicode data tables from the pinned Unicode files.

Writes the modules in src/confusable/_data/. They are committed, so installing
the package needs no network; CI runs this with --check and fails when the
committed tables differ from a fresh run.

    uv run python -m tools.generate_tables
    uv run python -m tools.generate_tables --check

Enumerated properties are written as runs: each (first code point, value)
entry lasts until the next one. Binary properties are written as (first, last)
ranges of the code points that have them. confusable._lookup reads both.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import cache
from pathlib import Path

from tools.unicode_sources import UNICODE_VERSION, fetch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "confusable" / "_data"
CODE_POINTS = 0x110000

# Hangul syllables decompose algorithmically (Unicode section 3.12), so the
# decomposition table leaves them out.
HANGUL_FIRST, HANGUL_LAST = 0xAC00, 0xD7A3


# Reading UCD files.


def _fields(line: str) -> list[str]:
    return [field.strip() for field in line.split("#", 1)[0].split(";")]


def _span(text: str) -> tuple[int, int]:
    first, _, last = text.partition("..")
    return int(first, 16), int(last or first, 16)


def _lines(path: Path) -> Iterator[tuple[int, int, list[str]]]:
    """Yield (first, last, fields) for each data line of a UCD-style file."""
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if line.split("#", 1)[0].strip():
                span, *fields = _fields(line)
                yield (*_span(span), fields)


def _missing(path: Path) -> Iterator[tuple[int, int, list[str]]]:
    """Yield the @missing default lines of a UCD file, in file order."""
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if line.startswith("# @missing:"):
                span, *fields = _fields(line.split(":", 1)[1])
                yield (*_span(span), fields)


@cache
def _aliases(prop: str) -> dict[str, str]:
    """Long value name -> short name for one property, from PropertyValueAliases."""
    out = {}
    with fetch("ucd/PropertyValueAliases.txt").open(encoding="utf-8") as lines:
        for line in lines:
            fields = _fields(line)
            if fields[0] == prop:
                out[fields[2]] = fields[1]
    return out


def _enumerated(
    path: Path,
    default: str,
    prop: str | None = None,
    aliases: dict[str, str] | None = None,
) -> list[str]:
    """Per-code-point values of an enumerated property.

    The default applies first, then @missing lines, then data lines. For files
    that hold several properties (DerivedCoreProperties.txt), prop selects one.
    """
    values = [default] * CODE_POINTS
    for source in (_missing(path), _lines(path)):
        for first, last, fields in source:
            if prop is not None:
                if fields[0] != prop:
                    continue
                fields = fields[1:]
            value = fields[0]
            if aliases is not None:
                value = aliases.get(value, value)
            values[first : last + 1] = [value] * (last - first + 1)
    return values


def _binary(path: Path, prop: str) -> list[bool]:
    """Per-code-point values of a binary property listed in a UCD file."""
    values = [False] * CODE_POINTS
    for first, last, fields in _lines(path):
        if fields[0] == prop:
            values[first : last + 1] = [True] * (last - first + 1)
    return values


@cache
def _unicode_data() -> dict[int, list[str]]:
    """UnicodeData.txt fields by code point, with First/Last ranges expanded."""
    out: dict[int, list[str]] = {}
    first: int | None = None
    with fetch("ucd/UnicodeData.txt").open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.rstrip("\n").split(";")
            cp = int(fields[0], 16)
            if fields[1].endswith(", First>"):
                first = cp
            elif fields[1].endswith(", Last>") and first is not None:
                for c in range(first, cp + 1):
                    out[c] = fields
                first = None
            else:
                out[cp] = fields
    return out


def _general_category() -> list[str]:
    data = _unicode_data()
    return [data[cp][2] if cp in data else "Cn" for cp in range(CODE_POINTS)]


# Writing Python.


def _runs(values: Sequence[str]) -> list[tuple[int, str]]:
    runs = [(0, values[0])]
    for cp in range(1, CODE_POINTS):
        if values[cp] != runs[-1][1]:
            runs.append((cp, values[cp]))
    return runs


def _ranges(flags: Sequence[bool]) -> list[tuple[int, int]]:
    out = []
    start: int | None = None
    for cp in range(CODE_POINTS + 1):
        flag = cp < CODE_POINTS and flags[cp]
        if flag and start is None:
            start = cp
        elif not flag and start is not None:
            out.append((start, cp - 1))
            start = None
    return out


def _string(code_points: Iterable[int]) -> str:
    """Write a Python string literal entirely in escapes."""
    escapes = (f"\\u{cp:04x}" if cp <= 0xFFFF else f"\\U{cp:08x}" for cp in code_points)
    return '"' + "".join(escapes) + '"'


def _emit_runs(name: str, values: Sequence[str], comment: str) -> list[str]:
    return [
        *(f"# {line}" for line in comment.splitlines()),
        f"{name}: tuple[tuple[int, str], ...] = (",
        *(f'    (0x{cp:04X}, "{value}"),' for cp, value in _runs(values)),
        ")",
        "",
    ]


def _emit_ranges(name: str, flags: Sequence[bool], comment: str) -> list[str]:
    return [
        *(f"# {line}" for line in comment.splitlines()),
        f"{name}: tuple[tuple[int, int], ...] = (",
        *(f"    (0x{first:04X}, 0x{last:04X})," for first, last in _ranges(flags)),
        ")",
        "",
    ]


def _module(summary: str, body: list[str]) -> str:
    header = [
        f'"""{summary}',
        "",
        f"Generated from Unicode {UNICODE_VERSION} data by",
        "tools/generate_tables.py; do not edit. Derived from Unicode data:",
        "see LICENSES/Unicode-3.0.txt.",
        '"""',
        "",
    ]
    while body and body[-1] == "":
        body = body[:-1]
    return "\n".join([*header, *body]) + "\n"


# The tables.


def package() -> str:
    return _module(
        "Unicode data tables for one pinned Unicode version.",
        [f'UNICODE_VERSION = "{UNICODE_VERSION}"'],
    )


def bidi() -> str:
    """Build the data for the Unicode Bidirectional Algorithm (UAX #9)."""
    classes = _enumerated(
        fetch("ucd/extracted/DerivedBidiClass.txt"), "L", aliases=_aliases("bc")
    )
    mirrors = {
        first: int(glyph, 16)
        for first, _, (glyph,) in _lines(fetch("ucd/BidiMirroring.txt"))
    }
    brackets = {
        first: (int(pair, 16), kind)
        for first, _, (pair, kind) in _lines(fetch("ucd/BidiBrackets.txt"))
    }
    # BD16 matches brackets under canonical equivalence; only singleton
    # canonical decompositions (U+2329, U+232A) can relate two brackets.
    canonical = {}
    for cp in brackets:
        decomposition = _unicode_data()[cp][5]
        if decomposition and not decomposition.startswith("<"):
            parts = decomposition.split()
            if len(parts) == 1:
                canonical[cp] = int(parts[0], 16)
    marks = [category[0] == "M" for category in _general_category()]
    return _module(
        "Unicode Bidirectional Algorithm (UAX #9) data.",
        [
            *_emit_runs(
                "BIDI_CLASS_RUNS",
                classes,
                "Bidi_Class. Unassigned code points get the defaults from the\n"
                "@missing lines of DerivedBidiClass.txt.",
            ),
            "# Bidi_Mirroring_Glyph, for the characters that have one.",
            "BIDI_MIRRORING_GLYPH: dict[int, int] = {",
            *(f"    0x{cp:04X}: 0x{to:04X}," for cp, to in sorted(mirrors.items())),
            "}",
            "",
            "# Bidi_Paired_Bracket and Bidi_Paired_Bracket_Type ('o' open, 'c' close).",
            "BIDI_BRACKETS: dict[int, tuple[int, str]] = {",
            *(
                f'    0x{cp:04X}: (0x{pair:04X}, "{kind}"),'
                for cp, (pair, kind) in sorted(brackets.items())
            ),
            "}",
            "",
            "# Brackets whose canonical decomposition is another single character.",
            "BRACKET_CANONICAL: dict[int, int] = {",
            *(f"    0x{cp:04X}: 0x{to:04X}," for cp, to in sorted(canonical.items())),
            "}",
            "",
            *_emit_ranges(
                "COMBINING_MARK_RANGES",
                marks,
                "General_Category=Mark (Mn, Mc, Me): the combining marks that rule\n"
                "L3 keeps after their base.",
            ),
        ],
    )


def normalization() -> str:
    """Build canonical decompositions and combining classes, for NFD."""
    data = _unicode_data()
    direct = {
        cp: [int(part, 16) for part in fields[5].split()]
        for cp, fields in data.items()
        if fields[5] and not fields[5].startswith("<")
    }

    def full(cp: int) -> list[int]:
        if cp not in direct:
            return [cp]
        return [c for part in direct[cp] for c in full(part)]

    combining = {cp: int(fields[3]) for cp, fields in data.items() if fields[3] != "0"}
    excluded = _binary(
        fetch("ucd/DerivedNormalizationProps.txt"), "Full_Composition_Exclusion"
    )
    # Primary composites: two-character canonical decompositions that NFC
    # recomposes, which excludes singletons and Full_Composition_Exclusion.
    compositions = {
        (parts[0], parts[1]): cp
        for cp, parts in direct.items()
        if len(parts) == 2 and not excluded[cp]
    }
    return _module(
        "Canonical decompositions, compositions and combining classes.",
        [
            "# The full canonical decomposition of every character that has one,",
            "# except Hangul syllables, which decompose algorithmically.",
            "CANONICAL_DECOMPOSITION: dict[int, str] = {",
            *(
                f"    0x{cp:04X}: {_string(full(cp))},"
                for cp in sorted(direct)
                if not HANGUL_FIRST <= cp <= HANGUL_LAST
            ),
            "}",
            "",
            "# Canonical_Combining_Class, for the characters where it is not 0.",
            "CANONICAL_COMBINING_CLASS: dict[int, int] = {",
            *(f"    0x{cp:04X}: {ccc}," for cp, ccc in sorted(combining.items())),
            "}",
            "",
            "# The primary composites NFC builds, by the pair they compose from,",
            "# except Hangul syllables, which compose algorithmically.",
            "CANONICAL_COMPOSITION: dict[tuple[int, int], int] = {",
            *(
                f"    (0x{first:04X}, 0x{second:04X}): 0x{cp:04X},"
                for (first, second), cp in sorted(compositions.items())
            ),
            "}",
        ],
    )


def confusables() -> str:
    """Build the UTS #39 prototype of every character that has one."""
    prototypes = {
        first: [int(part, 16) for part in target.split()]
        for first, _, (target, *_) in _lines(fetch("security/confusables.txt"))
    }
    return _module(
        "UTS #39 confusable prototypes, from confusables.txt.",
        [
            "# Characters without an entry are their own prototype.",
            "PROTOTYPES: dict[int, str] = {",
            *(
                f"    0x{cp:04X}: {_string(seq)},"
                for cp, seq in sorted(prototypes.items())
            ),
            "}",
        ],
    )


def scripts() -> str:
    """Build Script and Script_Extensions, as ISO 15924 codes."""
    script = _enumerated(fetch("ucd/Scripts.txt"), "Zzzz", aliases=_aliases("sc"))
    extensions = [""] * CODE_POINTS
    for first, last, (value,) in _lines(fetch("ucd/ScriptExtensions.txt")):
        codes = " ".join(sorted(value.split()))
        extensions[first : last + 1] = [codes] * (last - first + 1)
    return _module(
        "Script and Script_Extensions (UAX #24), as ISO 15924 codes.",
        [
            *_emit_runs("SCRIPT_RUNS", script, "Script."),
            *_emit_runs(
                "SCRIPT_EXTENSIONS_RUNS",
                extensions,
                "Script_Extensions, sorted, where ScriptExtensions.txt lists a value.\n"
                "An empty string means the default: just {Script}.",
            ),
        ],
    )


def identifiers() -> str:
    """Build the General Security Profile (UTS #39) and UAX #31 properties."""
    status = _enumerated(fetch("security/IdentifierStatus.txt"), "Restricted")
    types = _enumerated(fetch("security/IdentifierType.txt"), "Not_Character")
    core = fetch("ucd/DerivedCoreProperties.txt")
    return _module(
        "Identifier properties: UTS #39 Identifier_Status and Identifier_Type,\n"
        "and UAX #31 XID_Start and XID_Continue.",
        [
            *_emit_ranges(
                "IDENTIFIER_ALLOWED_RANGES",
                [value == "Allowed" for value in status],
                "Identifier_Status=Allowed: the General Security Profile.",
            ),
            *_emit_runs(
                "IDENTIFIER_TYPE_RUNS",
                types,
                "Identifier_Type: one or more types, in IdentifierType.txt order.",
            ),
            *_emit_ranges("XID_START_RANGES", _binary(core, "XID_Start"), "XID_Start."),
            *_emit_ranges(
                "XID_CONTINUE_RANGES", _binary(core, "XID_Continue"), "XID_Continue."
            ),
        ],
    )


def properties() -> str:
    """Build general properties: categories, invisibles, controls, dots, digits."""
    category = _general_category()
    core = fetch("ucd/DerivedCoreProperties.txt")
    props = fetch("ucd/PropList.txt")
    data = _unicode_data()
    # Each decimal system is ten consecutive code points from zero to nine.
    zeros = sorted(
        cp for cp, fields in data.items() if fields[2] == "Nd" and fields[6] == "0"
    )
    for zero in zeros:
        assert all(
            data[zero + d][2] == "Nd" and data[zero + d][6] == str(d) for d in range(10)
        )
    assert sum(1 for fields in data.values() if fields[2] == "Nd") == 10 * len(zeros)
    return _module(
        "General character properties.",
        [
            *_emit_runs("GENERAL_CATEGORY_RUNS", category, "General_Category."),
            *_emit_ranges(
                "DEFAULT_IGNORABLE_RANGES",
                _binary(core, "Default_Ignorable_Code_Point"),
                "Default_Ignorable_Code_Point.",
            ),
            *_emit_ranges(
                "BIDI_CONTROL_RANGES", _binary(props, "Bidi_Control"), "Bidi_Control."
            ),
            *_emit_ranges(
                "JOIN_CONTROL_RANGES", _binary(props, "Join_Control"), "Join_Control."
            ),
            *_emit_ranges(
                "SOFT_DOTTED_RANGES", _binary(props, "Soft_Dotted"), "Soft_Dotted."
            ),
            "# The zero of each decimal digit system (General_Category=Nd): the",
            "# system's digits are the ten code points from its zero.",
            "DECIMAL_ZEROS: tuple[int, ...] = (",
            *(f"    0x{zero:04X}," for zero in zeros),
            ")",
        ],
    )


def graphemes() -> str:
    """Build the properties UAX #29 extended grapheme clusters use."""
    return _module(
        "Properties for extended grapheme clusters (UAX #29).",
        [
            *_emit_runs(
                "GRAPHEME_CLUSTER_BREAK_RUNS",
                _enumerated(fetch("ucd/auxiliary/GraphemeBreakProperty.txt"), "Other"),
                "Grapheme_Cluster_Break.",
            ),
            *_emit_runs(
                "INDIC_CONJUNCT_BREAK_RUNS",
                _enumerated(
                    fetch("ucd/DerivedCoreProperties.txt"), "None", prop="InCB"
                ),
                "Indic_Conjunct_Break.",
            ),
            *_emit_ranges(
                "EXTENDED_PICTOGRAPHIC_RANGES",
                _binary(fetch("ucd/emoji/emoji-data.txt"), "Extended_Pictographic"),
                "Extended_Pictographic.",
            ),
        ],
    )


def joining() -> str:
    """Build the properties the joining-control contexts of UTS #39 use."""
    categories = _enumerated(fetch("ucd/IndicSyllabicCategory.txt"), "Other")
    return _module(
        "Properties for the joining-control contexts (UTS #39 section 3.1.1.1).",
        [
            *_emit_runs(
                "JOINING_TYPE_RUNS",
                _enumerated(
                    fetch("ucd/extracted/DerivedJoiningType.txt"),
                    "U",
                    aliases=_aliases("jt"),
                ),
                "Joining_Type, by short value name (U is Non_Joining).",
            ),
            *_emit_ranges(
                "VOWEL_DEPENDENT_RANGES",
                [value == "Vowel_Dependent" for value in categories],
                "Indic_Syllabic_Category=Vowel_Dependent.",
            ),
        ],
    )


def variation() -> str:
    """Build the valid variation sequences and the characters they use."""
    props = fetch("ucd/PropList.txt")
    sequences = set()
    for path in (
        "ucd/StandardizedVariants.txt",
        "ucd/emoji/emoji-variation-sequences.txt",
    ):
        with fetch(path).open(encoding="utf-8") as lines:
            for line in lines:
                if sequence := _fields(line)[0]:
                    base, selector = (int(part, 16) for part in sequence.split())
                    sequences.add((base, selector))
    return _module(
        "Variation sequences and the characters they are made of.",
        [
            *_emit_ranges(
                "VARIATION_SELECTOR_RANGES",
                _binary(props, "Variation_Selector"),
                "Variation_Selector.",
            ),
            *_emit_ranges(
                "UNIFIED_IDEOGRAPH_RANGES",
                _binary(props, "Unified_Ideograph"),
                "Unified_Ideograph: the bases of ideographic variation sequences.",
            ),
            "# Standardized variation sequences (StandardizedVariants.txt) and emoji",
            "# variation sequences (emoji-variation-sequences.txt): (base, selector).",
            "VARIATION_SEQUENCES: frozenset[tuple[int, int]] = frozenset({",
            *(f"    (0x{base:04X}, 0x{vs:04X})," for base, vs in sorted(sequences)),
            "})",
        ],
    )


# confusable_homoglyphs 3.3.1 reads Scripts.txt with this pattern
# (confusable_homoglyphs/cli.py): a range, its script and the General_Category
# the comment gives, where "L&" reads as "L".
_HOMOGLYPH_SCRIPT = re.compile(r"([0-9A-F]+)(?:\.\.([0-9A-F]+))?\W+(\w+)\s*#\s*(\w+)")
# The names in a confusables.txt comment: "( X \u2192 Y ) NAME X \u2192 NAME Y\t#".
_HOMOGLYPH_NAMES = re.compile("\\) ([^()\u2192]+) \u2192 ([^()\u2192]+)\t#")


def homoglyphs() -> str:
    """Build the data of confusable.compat.homoglyphs.

    The scripts and categories follow confusable_homoglyphs exactly. The
    confusable pairs come from the code point fields of confusables.txt, where
    that package reads the characters from the comments, which wrap
    right-to-left characters in LEFT-TO-RIGHT MARKs and show space-like
    characters as blanks; the names come from the comments, as there.
    """
    aliases: list[str] = []
    categories: list[str] = []
    ranges = []
    with fetch("ucd/Scripts.txt").open(encoding="utf-8") as lines:
        for line in lines:
            if found := _HOMOGLYPH_SCRIPT.findall(line):
                first, last, alias, category = found[0]
                alias = alias.upper()
                if alias not in aliases:
                    aliases.append(alias)
                if category not in categories:
                    categories.append(category)
                ranges.append(
                    (
                        int(first, 16),
                        int(last or first, 16),
                        aliases.index(alias),
                        categories.index(category),
                    )
                )
    ranges.sort()
    pairs = []
    names: dict[str, str] = {}
    with fetch("security/confusables.txt").open(encoding="utf-8") as lines:
        for line in lines:
            fields = _fields(line)
            if not fields[0]:
                continue
            source, target = ([int(cp, 16) for cp in f.split()] for f in fields[:2])
            match = _HOMOGLYPH_NAMES.search(line)
            assert match is not None, line
            for code_points, name in ((source, match[1]), (target, match[2])):
                # One name per character, and the same one on every line.
                assert len(name.split(", ")) == len(code_points), line
                key = _string(code_points)
                assert names.setdefault(key, name) == name, line
            pairs.append((_string(source), _string(target)))
    return _module(
        "Data for confusable.compat.homoglyphs, as confusable_homoglyphs has it.",
        [
            "# Script names in capitals, in the order Scripts.txt first uses them.",
            "ALIASES: tuple[str, ...] = (",
            *(f'    "{alias}",' for alias in aliases),
            ")",
            "# General_Category values as Scripts.txt comments give them, L& as L.",
            "CATEGORIES: tuple[str, ...] = (",
            *(f'    "{category}",' for category in categories),
            ")",
            "# (first, last, alias index, category index), sorted.",
            "SCRIPT_RANGES: tuple[tuple[int, int, int, int], ...] = (",
            *(f"    (0x{a:04X}, 0x{b:04X}, {i}, {j})," for a, b, i, j in ranges),
            ")",
            "# The confusables.txt lines as (source, target), in file order.",
            "PAIRS: tuple[tuple[str, str], ...] = (",
            *(f"    ({source}, {target})," for source, target in pairs),
            ")",
            "# The name of each source and target, as the comments give it.",
            "NAMES: dict[str, str] = {",
            *(f'    {key}: "{name}",' for key, name in names.items()),
            "}",
        ],
    )


def emoji() -> str:
    """Build the valid emoji tag sequences, the one legitimate use of Tags."""
    sequences = []
    with fetch("emoji/emoji-sequences.txt").open(encoding="utf-8") as lines:
        for line in lines:
            fields = _fields(line)
            if len(fields) > 1 and fields[1] == "RGI_Emoji_Tag_Sequence":
                sequences.append([int(part, 16) for part in fields[0].split()])
    return _module(
        "RGI emoji tag sequences (UTS #51), from emoji-sequences.txt.",
        [
            "# Subdivision flags such as England's: the only RGI uses of Tag",
            "# characters (U+E0020..U+E007F).",
            "RGI_EMOJI_TAG_SEQUENCES: frozenset[str] = frozenset({",
            *(f"    {_string(seq)}," for seq in sorted(sequences)),
            "})",
        ],
    )


TABLES: dict[str, Callable[[], str]] = {
    "__init__.py": package,
    "bidi.py": bidi,
    "confusables.py": confusables,
    "emoji.py": emoji,
    "graphemes.py": graphemes,
    "homoglyphs.py": homoglyphs,
    "identifiers.py": identifiers,
    "joining.py": joining,
    "normalization.py": normalization,
    "properties.py": properties,
    "scripts.py": scripts,
    "variation.py": variation,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="diff instead of writing")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, build in TABLES.items():
        text = build()
        target = DATA / name
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == text:
            continue
        stale.append(name)
        if not args.check:
            target.write_text(text, encoding="utf-8", newline="\n")
    extra = sorted(p.name for p in DATA.glob("*.py") if p.name not in TABLES)
    if args.check and (stale or extra):
        raise SystemExit(f"tables differ from a fresh run: {', '.join(stale + extra)}")
    for name in extra:
        (DATA / name).unlink()
    print(f"{len(stale)} stale, {len(extra)} removed, {len(TABLES)} tables")


if __name__ == "__main__":
    main()
