"""Generate the package's Unicode data tables from the pinned Unicode files.

Writes the modules in src/confusable/_data/. They are committed, so installing
the package needs no network; CI runs this with --check and fails when the
committed tables differ from a fresh run.

    uv run python -m tools.generate_tables
    uv run python -m tools.generate_tables --check
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from pathlib import Path

from tools.unicode_sources import UNICODE_VERSION, fetch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "confusable" / "_data"
CODE_POINTS = 0x110000


def _lines(path: Path) -> Iterator[tuple[int, int, list[str]]]:
    """Yield (first, last, fields) for each data line of a UCD-style file."""
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            data = line.split("#", 1)[0].strip()
            if not data:
                continue
            span, *fields = (field.strip() for field in data.split(";"))
            first, _, last = span.partition("..")
            yield int(first, 16), int(last or first, 16), fields


def _missing(path: Path) -> Iterator[tuple[int, int, str]]:
    """Yield the @missing default lines of a UCD file, in file order."""
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if line.startswith("# @missing:"):
                span, value = (f.strip() for f in line.split(":", 1)[1].split(";"))
                first, _, last = span.partition("..")
                yield int(first, 16), int(last or first, 16), value


def _value_aliases(prop: str) -> dict[str, str]:
    """Long value name -> short name for one property, from PropertyValueAliases."""
    aliases = {}
    with fetch("ucd/PropertyValueAliases.txt").open(encoding="utf-8") as lines:
        for line in lines:
            fields = [field.strip() for field in line.split("#", 1)[0].split(";")]
            if fields[0] == prop:
                aliases[fields[2]] = fields[1]
    return aliases


def _runs(values: list[str]) -> list[tuple[int, str]]:
    """Compress per-code-point values into (first code point, value) runs."""
    runs = [(0, values[0])]
    for cp in range(1, CODE_POINTS):
        if values[cp] != runs[-1][1]:
            runs.append((cp, values[cp]))
    return runs


def _unicode_data() -> dict[int, list[str]]:
    """UnicodeData.txt fields by code point, with First/Last ranges expanded."""
    fields_by_cp: dict[int, list[str]] = {}
    first: int | None = None
    with fetch("ucd/UnicodeData.txt").open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.rstrip("\n").split(";")
            cp = int(fields[0], 16)
            if fields[1].endswith(", First>"):
                first = cp
            elif fields[1].endswith(", Last>") and first is not None:
                for c in range(first, cp + 1):
                    fields_by_cp[c] = fields
                first = None
            else:
                fields_by_cp[cp] = fields
    return fields_by_cp


def bidi() -> str:
    """Build the data the Unicode Bidirectional Algorithm (UAX #9) needs."""
    path = fetch("ucd/extracted/DerivedBidiClass.txt")
    short = _value_aliases("bc")
    classes = ["L"] * CODE_POINTS
    for first, last, value in _missing(path):
        for cp in range(first, last + 1):
            classes[cp] = short[value]
    for first, last, (value,) in _lines(path):
        for cp in range(first, last + 1):
            classes[cp] = value

    mirrors = {
        first: int(glyph, 16)
        for first, _, (glyph,) in _lines(fetch("ucd/BidiMirroring.txt"))
    }
    brackets = {
        first: (int(pair, 16), kind)
        for first, _, (pair, kind) in _lines(fetch("ucd/BidiBrackets.txt"))
    }

    unicode_data = _unicode_data()
    # BD16 matches brackets under canonical equivalence; only singleton
    # canonical decompositions (U+2329, U+232A) can relate two brackets.
    canonical = {}
    for cp in brackets:
        decomposition = unicode_data[cp][5]
        if decomposition and not decomposition.startswith("<"):
            parts = decomposition.split()
            if len(parts) == 1:
                canonical[cp] = int(parts[0], 16)
    marks = [
        "Y" if unicode_data.get(cp, ["", "", "Cn"])[2][0] == "M" else "N"
        for cp in range(CODE_POINTS)
    ]

    out = [
        _header("Unicode Bidirectional Algorithm (UAX #9) data."),
        "# Bidi_Class, as runs: each entry starts a run of code points with that",
        "# class, which lasts until the next entry. Unassigned code points get",
        "# the defaults from the @missing lines of DerivedBidiClass.txt.",
        "BIDI_CLASS_RUNS: tuple[tuple[int, str], ...] = (",
        *(f'    (0x{cp:04X}, "{value}"),' for cp, value in _runs(classes)),
        ")",
        "",
        "# Bidi_Mirroring_Glyph, for the characters that have one.",
        "BIDI_MIRRORING_GLYPH: dict[int, int] = {",
        *(f"    0x{cp:04X}: 0x{glyph:04X}," for cp, glyph in sorted(mirrors.items())),
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
        "# Runs of General_Category=Mark (Mn, Mc, Me), the combining marks that",
        "# rule L3 keeps after their base: (first, last) code points.",
        "COMBINING_MARK_RANGES: tuple[tuple[int, int], ...] = (",
        *(f"    (0x{first:04X}, 0x{last:04X})," for first, last in _true_ranges(marks)),
        ")",
    ]
    return "\n".join(out) + "\n"


def _true_ranges(flags: list[str]) -> Iterator[tuple[int, int]]:
    start: int | None = None
    for cp, flag in enumerate([*flags, "N"]):
        if flag == "Y" and start is None:
            start = cp
        elif flag != "Y" and start is not None:
            yield start, cp - 1
            start = None


def _header(summary: str) -> str:
    return "\n".join(
        [
            f'"""{summary}',
            "",
            f"Generated from Unicode {UNICODE_VERSION} data by",
            "tools/generate_tables.py; do not edit. Derived from Unicode data:",
            "see LICENSES/Unicode-3.0.txt.",
            '"""',
            "",
            f'UNICODE_VERSION = "{UNICODE_VERSION}"',
            "",
        ]
    )


TABLES: dict[str, Callable[[], str]] = {"bidi.py": bidi}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="diff instead of writing")
    args = parser.parse_args()
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
    if args.check and stale:
        raise SystemExit(f"tables differ from a fresh run: {', '.join(stale)}")
    print(f"{'stale' if stale else 'up to date'}: {', '.join(TABLES)}")


if __name__ == "__main__":
    main()
