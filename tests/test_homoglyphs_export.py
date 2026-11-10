"""export() writes confusable_homoglyphs' data files, for its CONFUSABLE_DATA."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from confusable.compat import homoglyphs
from confusable.compat.homoglyphs import __main__ as cli
from confusable.compat.homoglyphs import categories, confusables
from tests import homoglyphs_package
from tests.conformance import oracle_data

ALEF = "\u0627"  # ARABIC LETTER ALEF, which looks like l
VAV = "\u05d5"  # HEBREW LETTER VAV, which looks like l too
CYRILLIC_A = "\u0430"
# With preferred_aliases=["latin"], the package's own data finds the Cyrillic
# look-alike and misses the Arabic and Hebrew ones.
REPRODUCERS = ["pa" + ALEF + "ypal", "pa" + VAV + "pal", "p" + CYRILLIC_A + "ypal"]


def test_export_writes_the_packages_two_files(tmp_path: Path) -> None:
    directory = tmp_path / "data"  # created
    paths = homoglyphs.export(directory)
    assert paths == [
        str(directory / "categories.json"),
        str(directory / "confusables.json"),
    ]
    for path in paths:
        # The package opens its files without naming an encoding: ASCII only.
        assert Path(path).read_bytes().isascii()
    assert json.loads(Path(paths[0]).read_text()) == categories.categories_data
    assert json.loads(Path(paths[1]).read_text()) == confusables.confusables_data
    # Exporting again overwrites.
    Path(paths[1]).write_text("{}")
    homoglyphs.export(directory)
    assert json.loads(Path(paths[1]).read_text()) == confusables.confusables_data


def test_files_have_the_packages_layout(tmp_path: Path) -> None:
    homoglyphs.export(tmp_path)
    data = json.loads((tmp_path / "categories.json").read_text(encoding="utf-8"))
    assert list(data) == ["iso_15924_aliases", "categories", "code_points_ranges"]
    assert data["iso_15924_aliases"][:2] == ["COMMON", "LATIN"]
    assert "Nd" in data["categories"]
    for first, last, alias_index, category_index in data["code_points_ranges"]:
        assert 0 <= first <= last <= 0x10FFFF
        assert data["iso_15924_aliases"][alias_index]
        assert data["categories"][category_index]
    # The file the package's own generator makes from the pinned Scripts.txt.
    assert data == oracle_data.homoglyph_data()["categories"]
    data = json.loads((tmp_path / "confusables.json").read_text(encoding="utf-8"))
    assert all(isinstance(key, str) and key for key in data)
    for found in data.values():
        assert found
        assert all(list(homoglyph) == ["c", "n"] for homoglyph in found)
    assert {"c": "\u03c1", "n": "GREEK SMALL LETTER RHO"} in data["p"]
    # The keys the package's own data lacks (see test_homoglyphs.py).
    assert data[ALEF] == [{"c": "l", "n": "LATIN SMALL LETTER L"}]
    assert data[VAV] == [{"c": "l", "n": "LATIN SMALL LETTER L"}]
    assert "\u3164" in data  # HANGUL FILLER


def test_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    directory = tmp_path / "out"
    assert cli.main(["export", str(directory)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        str(directory / "categories.json"),
        str(directory / "confusables.json"),
    ]
    written = json.loads((directory / "confusables.json").read_text())
    assert written == confusables.confusables_data


def test_command_line_needs_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2
    assert "required: COMMAND" in capsys.readouterr().err


def test_module_runs_as_a_script(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "confusable.compat.homoglyphs", "export", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        str(tmp_path / "categories.json"),
        str(tmp_path / "confusables.json"),
    ]


def test_the_package_reads_the_exported_files(tmp_path: Path) -> None:
    """confusable_homoglyphs 3.3.1 itself, on the exported files: the fixtures.

    The fixtures hold what the package returns on corrected data
    (tools/oracles/homoglyphs/oracle.py). The exported files are that data,
    so the unchanged package, reading them through CONFUSABLE_DATA, must
    return the fixtures' results for every string of the corpus. Skips when
    the package is not installed (tests/homoglyphs_package.py).
    """
    data_dir = tmp_path / "data"
    homoglyphs.export(data_dir)
    cases = oracle_data.homoglyph_cases()
    strings = [case.text for case in cases] + REPRODUCERS
    shipped = homoglyphs_package.run(strings, None, tmp_path)
    exported = homoglyphs_package.run(strings, data_dir, tmp_path)
    # The real package, not this module under another name.
    assert "confusable_homoglyphs" in Path(exported["module"]).parts
    assert shipped["keys"] < exported["keys"] == len(confusables.confusables_data)

    expected = [
        [case.unique_aliases, list(case.mixed), list(case.dangerous), case.confusable]
        for case in cases
    ]
    mismatches = [
        oracle_data.hex_seq(case.text)
        for case, got, want in zip(cases, exported["results"], expected, strict=False)
        if got != want
    ]
    assert mismatches == [], mismatches[:20]

    # The reproducers. is_confusable(preferred_aliases=["latin"]) finds the
    # Arabic and Hebrew look-alikes only with the exported data, and the
    # Cyrillic one with both; is_dangerous() is True for all three with both,
    # since the Latin letters have look-alikes of their own.
    n = len(cases)
    latin = [bool(result[3][1]) for result in shipped["results"][n:]]
    assert latin == [False, False, True]
    latin = [bool(result[3][1]) for result in exported["results"][n:]]
    assert latin == [True, True, True]
    for output in (shipped, exported):
        assert [result[2][0] for result in output["results"][n:]] == [True] * 3
