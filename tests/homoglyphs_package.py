"""Run confusable_homoglyphs 3.3.1 itself, in a subprocess, for the tests that need it.

Ordinary test runs need only the committed fixtures (C-CORRECT-1), so the
package is not a test dependency. The tests that must run the real package,
on the data files confusable.compat.homoglyphs exports for it, run it in
whichever interpreter has it: this one, or the one tools/oracles/generate.py
builds into tools/oracles/homoglyphs/.build/venv to make the fixtures, with
the checkout's src/ on its path. Without either, they skip.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORACLE_VENV = ROOT / "tools" / "oracles" / "homoglyphs" / ".build" / "venv"
VERSION = "3.3.1"

# Runs in the interpreter that has the package. argv[1] names a file of
# strings, one per line as space-separated hex code points; the output is
# JSON: the package's version, the file its confusables module came from, the
# number of keys in its data and, for each string, what its functions return,
# in the form of tests/conformance/fixtures/homoglyphs.txt.gz (see
# tests.conformance.oracle_data.HomoglyphCase).
SCRIPT = """
import importlib.metadata
import json
import sys

from confusable_homoglyphs import categories, confusables

ALLOWED = [None, [], ["common", "latin"]]
DANGEROUS = [[], ["latin"]]
PREFERRED = [[], ["latin"], ["greek"], ["latin", "common"], ["cyrillic"]]

with open(sys.argv[1], encoding="utf-8") as f:
    strings = ["".join(chr(int(t, 16)) for t in line.split()) for line in f]


def summary(found):
    if found is False:
        return False
    return [[f["character"], f["alias"], len(f["homoglyphs"])] for f in found]


results = [
    [
        sorted(categories.unique_aliases(s)),
        [confusables.is_mixed_script(s, *([] if a is None else [a])) for a in ALLOWED],
        [confusables.is_dangerous(s, preferred_aliases=p) for p in DANGEROUS],
        [
            summary(confusables.is_confusable(s, greedy=True, preferred_aliases=p))
            for p in PREFERRED
        ],
    ]
    for s in strings
]
json.dump(
    {
        "version": importlib.metadata.version("confusable_homoglyphs"),
        "module": confusables.__file__,
        "keys": len(confusables.confusables_data),
        "results": results,
    },
    sys.stdout,
)
"""


def interpreter() -> tuple[str, dict[str, str]]:
    """Return a Python that has confusable_homoglyphs and its environment, or skip."""
    env = dict(os.environ)
    if importlib.util.find_spec("confusable_homoglyphs") is not None:
        return sys.executable, env
    for python in (
        ORACLE_VENV / "bin" / "python",
        ORACLE_VENV / "Scripts" / "python.exe",
    ):
        if python.exists():
            env["PYTHONPATH"] = str(ROOT / "src")
            return str(python), env
    pytest.skip(
        "confusable_homoglyphs 3.3.1 is not installed; see tools/oracles/README.md"
    )


def run(strings: list[str], data_dir: Path | None, work: Path) -> dict[str, Any]:
    """Run the package's functions on strings and return SCRIPT's output.

    With data_dir, the package reads its data files from there, through its
    CONFUSABLE_DATA environment variable; without it, the files it ships.
    """
    python, env = interpreter()
    env.pop("CONFUSABLE_DATA", None)
    if data_dir is not None:
        env["CONFUSABLE_DATA"] = str(data_dir)
    strings_file = work / "strings.txt"
    strings_file.write_text(
        "".join(" ".join(f"{ord(c):04X}" for c in s) + "\n" for s in strings),
        encoding="utf-8",
    )
    result = subprocess.run(
        [python, "-c", SCRIPT, str(strings_file)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output: dict[str, Any] = json.loads(result.stdout)
    if output["version"] != VERSION:
        pytest.skip(
            f"confusable_homoglyphs {VERSION} is needed, not {output['version']}"
        )
    return output
