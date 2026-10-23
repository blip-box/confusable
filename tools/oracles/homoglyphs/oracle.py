"""Run confusable_homoglyphs 3.3.1 as the oracle for confusable.compat.homoglyphs.

Runs inside the virtual environment that tools/oracles/generate.py builds from
requirements.txt, with no network access:

    python -I oracle.py SCRIPTS_TXT CONFUSABLES_TXT STRINGS OUT_DIR

It writes two files to OUT_DIR:

- data.json: the data files that the package's own generator
  (confusable_homoglyphs.cli) makes from the pinned Unicode files, as they are.
- results.txt: what the package's functions return for each input string,
  run on corrected data (see corrected_confusables), one tab-separated line
  per string, in the format tools/oracles/generate.py documents.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType

# The character names in a confusables.txt comment, after the characters:
# "( X \u2192 Y ) NAME OF X \u2192 NAME OF Y\t#". Names have no parentheses.
NAMES = re.compile("\\) ([^()\u2192]+) \u2192 ([^()\u2192]+)\t#")

# Preferred aliases for is_confusable, and allowed aliases for is_mixed_script.
PREFERRED: list[list[str]] = [
    [],
    ["latin"],
    ["greek"],
    ["latin", "common"],
    ["cyrillic"],
]
ALLOWED: list[list[str] | None] = [None, [], ["common", "latin"]]  # None: ['COMMON']
DANGEROUS: list[list[str]] = [[], ["latin"]]


def text(field: str) -> str:
    return "".join(chr(int(part, 16)) for part in field.split())


def corrected_confusables(path: Path) -> dict[str, list[dict[str, str]]]:
    """Build confusables.json as the generator means to, from code points.

    The generator reads the characters from each line's comment, where
    confusables.txt wraps right-to-left characters in LEFT-TO-RIGHT MARKs and
    shows space-like characters as blanks its pattern cannot match. These
    come from the line's code point fields instead; the names, and the order
    of entries, are as the generator has them.
    """
    data: dict[str, list[dict[str, str]]] = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        fields = line.split("#", 1)[0].split(";")
        if len(fields) < 3:
            continue
        source, target = text(fields[0]), text(fields[1])
        match = NAMES.search(line)
        assert match is not None, line
        data.setdefault(source, []).append({"c": target, "n": match[2]})
        data.setdefault(target, []).append({"c": source, "n": match[1]})
    return data


def results(string: str, categories: ModuleType, confusables: ModuleType) -> str:
    """One line of results.txt: the package's answers for one string."""
    c = confusables
    mixed = "".join(
        "TF"[not c.is_mixed_script(string, *([] if a is None else [a]))]
        for a in ALLOWED
    )
    dangerous = "".join(
        "TF"[not c.is_dangerous(string, preferred_aliases=p)] for p in DANGEROUS
    )
    confusable = []
    for preferred in PREFERRED:
        found = c.is_confusable(string, greedy=True, preferred_aliases=preferred)
        confusable.append(
            False
            if found is False
            else [[f["character"], f["alias"], len(f["homoglyphs"])] for f in found]
        )
    aliases = " ".join(sorted(categories.unique_aliases(string)))
    return "\t".join(
        [
            " ".join(f"{ord(ch):04X}" for ch in string),
            aliases,
            mixed,
            dangerous,
            json.dumps(confusable, separators=(",", ":")),
        ]
    )


def main() -> None:
    scripts_txt, confusables_txt, strings_path, out_dir = map(Path, sys.argv[1:5])
    from confusable_homoglyphs import cli  # type: ignore[import-not-found]

    sources = {"Scripts.txt": scripts_txt, "confusables.txt": confusables_txt}

    def get(url: str, timeout: float | None = None) -> list[str]:
        return sources[url.rsplit("/", 1)[1]].read_text(encoding="utf-8").split("\n")

    cli.get = get  # read the pinned files, not the network
    with tempfile.TemporaryDirectory() as raw:
        os.environ["CONFUSABLE_DATA"] = raw
        cli.generate_categories()
        cli.generate_confusables()
        data = {
            name: json.loads((Path(raw) / f"{name}.json").read_text(encoding="utf-8"))
            for name in ("categories", "confusables")
        }
    (out_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")

    with tempfile.TemporaryDirectory() as fixed:
        (Path(fixed) / "categories.json").write_text(
            json.dumps(data["categories"]), encoding="utf-8"
        )
        (Path(fixed) / "confusables.json").write_text(
            json.dumps(corrected_confusables(confusables_txt)), encoding="utf-8"
        )
        os.environ["CONFUSABLE_DATA"] = fixed
        from confusable_homoglyphs import categories, confusables

        # The modules load their data on import: reload them to read these.
        importlib.reload(categories)
        importlib.reload(confusables)
        # One string per line, the empty string included.
        lines = strings_path.read_text(encoding="utf-8").split("\n")[:-1]
        out = [results(text(line), categories, confusables) for line in lines]
    (out_dir / "results.txt").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
