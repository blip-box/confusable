"""Guild's oracle check: whether the committed fixtures confirm a bug report.

Run by the intake job of .github/workflows/guild-triage.yml, from the base
branch, with no secrets:

    python -I tools/guild_oracle_check.py --snapshot snapshot.json --out oracle.txt

The snapshot is the escaped record that guildkit makes of the issue (every
character outside printable ASCII written as U+XXXX). The bug form's fields
give the code points, the function called and the expected and actual
results. This script runs the library on the reproducer and looks the same
input up in the conformance fixtures, which hold ICU's answers for every
single code point and for a corpus of strings and pairs. It writes one word:

    confirms        the oracle's answer differs from the library's: a bug
    disagrees       the oracle agrees with the library; a steward reads the spec
    not_applicable  no reproducer in the text
    not_run         a reproducer, but nothing in the fixtures answers it
    error           this script failed

Nothing from the issue is executed. The fields are data: code points become
a string, the function name is matched against a fixed list, and the other
arguments are read with regular expressions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import confusable  # noqa: E402
from tests.conformance import adapter, oracle_data  # noqa: E402

Verdict = Literal["confirms", "disagrees", "not_applicable", "not_run", "error"]

# The bug form's labels, as the escaped plain text shows them.
LABELS = (
    "Summary",
    "Code points",
    "Function called",
    "Expected result",
    "Actual result",
    "Library version",
    "Specification clause",
)
_CODE_POINT = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_CALL = re.compile(r"^\s*([a-z_]+)\s*\((.*)\)\s*$", re.DOTALL)
_DIRECTION = re.compile(r"direction\s*=\s*[\"']?(ltr|rtl|auto|None)[\"']?")
_JOINING = re.compile(r"joining_controls\s*=\s*True")
_QUOTED = re.compile(r"[\"']([^\"']*)[\"']")


def fields(body: str) -> dict[str, str]:
    """Return the form fields in the escaped body, by label."""
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped in LABELS:
            current = stripped
            found[current] = []
        elif current is not None and stripped:
            found[current].append(stripped)
    return {label: "\n".join(lines) for label, lines in found.items()}


def decode(value: str) -> str:
    """Return the characters that the U+XXXX tokens in value name."""
    return "".join(chr(int(m, 16)) for m in _CODE_POINT.findall(value))


def escape(value: object) -> str:
    """Return value as ASCII text, for a public log."""
    return "".join(
        c if c in "\n\t" or 0x20 <= ord(c) <= 0x7E else f"U+{ord(c):04X}"
        for c in str(value)
    )


def other_argument(arguments: str) -> str | None:
    """Return the second positional argument of a call such as match(text, ...)."""
    rest = arguments.split(",", 1)
    if len(rest) < 2:
        return None
    second = re.split(r",\s*[a-z_]+\s*=", rest[1], maxsplit=1)[0]
    if _CODE_POINT.search(second):
        return decode(second)
    quoted = _QUOTED.search(second)
    return quoted[1] if quoted else None


@cache
def string_cases() -> dict[str, oracle_data.StringCase]:
    return {case.text: case for case in oracle_data.strings()}


@cache
def pair_cases() -> dict[tuple[str, str], oracle_data.PairCase]:
    cases: dict[tuple[str, str], oracle_data.PairCase] = {}
    for case in oracle_data.pairs():
        cases[case.a, case.b] = case
        cases.setdefault((case.b, case.a), case)
    return cases


def _skeleton(text: str, direction: str) -> tuple[object, object] | None:
    if direction == "auto":
        return None
    case = string_cases().get(text)
    if case is not None:
        oracle = {
            "ltr": case.skeleton,
            "None": case.internal_skeleton,
            "rtl": case.rtl_skeleton,
        }[direction]
    elif len(text) == 1:
        plain = oracle_data.skeletons().get(text, text)
        oracle = (
            oracle_data.rtl_skeletons().get(text, plain)
            if direction == "rtl"
            else plain
        )
    else:
        return None
    return oracle, _SKELETON_FUNCTION[direction](text)


_SKELETON_FUNCTION: dict[str, Callable[[str], str]] = {
    "ltr": adapter.skeleton,
    "None": adapter.internal_skeleton,
    "rtl": lambda t: adapter.bidi_skeleton(t, "RTL"),
}
_SKELETON_KIND: dict[str, Literal["skeleton", "internal", "rtl"]] = {
    "ltr": "skeleton",
    "None": "internal",
    "rtl": "rtl",
}


def _match(
    text: str, other: str | None, direction: str
) -> tuple[object, object] | None:
    if other is None or direction == "auto":
        return None
    case = pair_cases().get((text, other))
    if case is None:
        return None
    kind = _SKELETON_KIND[direction]
    oracle = {"skeleton": case.confusable, "internal": case.internal, "rtl": case.rtl}[
        kind
    ]
    return oracle, adapter.confusable_classes(text, other, kind)


def _from_corpus(
    text: str,
    oracle: Callable[[oracle_data.StringCase], object],
    library: Callable[[str], object],
) -> tuple[object, object] | None:
    case = string_cases().get(text)
    if case is None:
        return None
    return oracle(case), library(text)


def _property(text: str, name: str) -> tuple[object, object] | None:
    if len(text) != 1:
        return None
    cp = ord(text)
    return oracle_data.properties()[name](cp), adapter.property_value(name, cp)


def _unlikely_marks(text: str) -> tuple[object, object] | None:
    # ICU's INVISIBLE check is the repeated-mark rule only; the library also
    # flags more than four marks, which no oracle checks.
    if confusable.has_unlikely_marks(text) != adapter.repeated_nonspacing_mark(text):
        return None
    return _from_corpus(
        text, lambda c: "INVISIBLE" in c.failed_checks, confusable.has_unlikely_marks
    )


def compare(
    function: str, text: str, other: str | None, direction: str, joining: bool
) -> tuple[object, object] | None:
    """Return (oracle's answer, library's answer), or None when no fixture answers."""
    if joining and function in ("is_allowed", "restriction_level"):
        return None  # the fixtures use the default profile
    match function:
        case "skeleton":
            return _skeleton(text, direction)
        case "match":
            return _match(text, other, direction)
        case "is_mixed_script":
            return _from_corpus(
                text, lambda c: c.resolved_script_set == "", confusable.is_mixed_script
            )
        case "restriction_level":
            return _from_corpus(
                text, lambda c: c.restriction_level, adapter.restriction_level
            )
        case "is_allowed":
            return _from_corpus(
                text,
                lambda c: "CHAR_LIMIT" not in c.failed_checks,
                confusable.is_allowed,
            )
        case "identifier_status":
            return _property(text, "Identifier_Status")
        case "identifier_types":
            return _property(text, "Identifier_Type")
        case "isxidstart":
            return _property(text, "XID_Start")
        case "isxidcontinue":
            return _property(text, "XID_Continue")
        case "has_mixed_numbers":
            return _from_corpus(
                text,
                lambda c: "MIXED_NUMBERS" in c.failed_checks,
                confusable.has_mixed_numbers,
            )
        case "has_unlikely_marks":
            return _unlikely_marks(text)
        case "has_hidden_overlay":
            return _from_corpus(
                text,
                lambda c: "HIDDEN_OVERLAY" in c.failed_checks,
                confusable.has_hidden_overlay,
            )
        case "iter_graphemes":
            return _from_corpus(
                text, lambda c: c.grapheme_boundaries, adapter.grapheme_boundaries
            )
        case _:
            return None


def verdict(body: str, log: Callable[[str], None] = lambda line: None) -> Verdict:
    """Return the oracle check's verdict on the escaped issue body."""
    form = fields(body)
    text = decode(form.get("Code points", ""))
    call = _CALL.match(form.get("Function called", ""))
    if not text or call is None:
        return "not_applicable"
    function, arguments = call[1], call[2]
    direction_match = _DIRECTION.search(arguments)
    direction = direction_match[1] if direction_match else "ltr"
    result = compare(
        function,
        text,
        other_argument(arguments),
        direction,
        bool(_JOINING.search(arguments)),
    )
    expected = escape(form.get("Expected result", ""))
    log(f"function: {function}; text: {escape(text)}; expected: {expected}")
    if result is None:
        log("no fixture answers this input")
        return "not_run"
    oracle, library = result
    log(f"oracle: {escape(oracle)}; library: {escape(library)}")
    return "disagrees" if oracle == library else "confirms"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        word: Verdict = verdict(str(snapshot.get("body", "")), print)
    except Exception as e:
        print(f"oracle check failed: {type(e).__name__}", file=sys.stderr)
        word = "error"
    args.out.write_text(word + "\n", encoding="ascii")
    print(f"verdict: {word}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
