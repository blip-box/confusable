"""No invisible, bidirectional or look-alike characters in the project's source.

A library that detects Trojan Source attacks and look-alikes must not contain
them. Python source is ASCII: write any other character as an escape, which
also keeps look-alikes out. Other text files may use visible non-ASCII
characters (a copyright sign), but none that are invisible or reorder text.
"""

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from confusable._data import properties
from confusable._lookup import Ranges, Runs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IGNORABLE = Ranges(properties.DEFAULT_IGNORABLE_RANGES)
BIDI_CONTROL = Ranges(properties.BIDI_CONTROL_RANGES)
GENERAL_CATEGORY = Runs(properties.GENERAL_CATEGORY_RUNS)
# Controls, formatting, surrogates, private use and unassigned code points.
HIDDEN_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn"}
WHITESPACE_CONTROLS = {"\t", "\n", "\r"}


def text_files() -> Iterator[tuple[Path, str]]:
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    for name in listing.decode("utf-8").split("\0"):
        # Fixtures are generated, hex-encoded and checked by generate.py --check.
        if not name or name.startswith("tests/conformance/fixtures/"):
            continue
        try:
            yield ROOT / name, (ROOT / name).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def hidden(c: str) -> bool:
    cp = ord(c)
    if c in WHITESPACE_CONTROLS:
        return False
    return (
        cp in DEFAULT_IGNORABLE
        or cp in BIDI_CONTROL
        or GENERAL_CATEGORY[cp] in HIDDEN_CATEGORIES
    )


def test_no_invisible_or_bidi_characters() -> None:
    found = sorted(
        f"{path.relative_to(ROOT)}: U+{ord(c):04X}"
        for path, text in text_files()
        for c in set(text)
        if hidden(c)
    )
    assert found == []


def test_python_source_is_ascii() -> None:
    found = sorted(
        str(path.relative_to(ROOT))
        for path, text in text_files()
        if path.suffix == ".py" and not text.isascii()
    )
    assert found == []
