"""CHARTER.md keeps its shape: stable clause IDs and real enforcement pointers.

Agents cite clauses by ID, so an ID must never change meaning silently: IDs are
unique and consecutive within their area, every ID the file cites is defined,
and every path the enforcement table names exists. The files agents read as
instructions are ASCII (C-SEC-1), so no look-alike can change what they say.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHARTER = (ROOT / "CHARTER.md").read_text(encoding="utf-8")
# A clause starts a paragraph with its bold ID, as in "**C-SPEC-1** Follow ...".
DEFINITION = re.compile(r"^\*\*(C-([A-Z]+)-(\d+))\*\*", re.MULTILINE)
CITATION = re.compile(r"\bC-[A-Z]+-\d+\b")
INSTRUCTION_FILES = ("AGENTS.md", "CHARTER.md", "CLAUDE.md")


def definitions() -> list[tuple[str, str, int]]:
    return [(m[1], m[2], int(m[3])) for m in DEFINITION.finditer(CHARTER)]


def test_clause_ids_are_unique_and_consecutive_within_each_area() -> None:
    ids = [clause for clause, _, _ in definitions()]
    assert len(ids) > 20
    assert len(ids) == len(set(ids))
    numbers: dict[str, list[int]] = {}
    for _, area, number in definitions():
        numbers.setdefault(area, []).append(number)
    for area, found in numbers.items():
        assert found == list(range(1, len(found) + 1)), area


def test_every_cited_clause_is_defined() -> None:
    defined = {clause for clause, _, _ in definitions()}
    assert sorted(set(CITATION.findall(CHARTER)) - defined) == []


def test_enforcement_table_names_paths_that_exist() -> None:
    _, table = CHARTER.split("\n## Enforcement\n", 1)
    paths = re.findall(r"`([^`]+)`", table)
    assert len(paths) > 10
    assert [p for p in paths if not (ROOT / p).exists()] == []


@pytest.mark.parametrize("name", INSTRUCTION_FILES)
def test_instruction_files_are_ascii(name: str) -> None:
    assert (ROOT / name).read_text(encoding="utf-8").isascii()


@pytest.mark.parametrize("name", ["AGENTS.md", "README.md"])
def test_handbook_and_readme_link_to_the_charter(name: str) -> None:
    assert "(CHARTER.md)" in (ROOT / name).read_text(encoding="utf-8")
