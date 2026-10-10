"""Checks on the fixtures themselves, which need no library code.

They catch a stale or hand-edited fixture, a curated attack that does not do
what its entry says, and data that breaks a guarantee UTS #39 makes.
"""

from __future__ import annotations

import pytest

from tests.conformance import oracle_data
from tests.conformance.attacks import ATTACKS

FIXTURE_FILES = (
    "skeleton.txt",
    "skeleton-rtl.txt",
    "nfd.txt",
    "properties.txt",
    "strings.txt",
    "pairs.txt",
)


@pytest.mark.parametrize("name", FIXTURE_FILES)
def test_fixture_targets_the_pinned_unicode_version(name: str) -> None:
    first = oracle_data.header(name)[0]
    assert f"Unicode {oracle_data.UNICODE_VERSION}." in first


def test_grapheme_break_test_is_the_pinned_version() -> None:
    first = oracle_data.header("GraphemeBreakTest.txt")[0]
    assert first == f"# GraphemeBreakTest-{oracle_data.UNICODE_VERSION}.txt"


def test_every_oracle_difference_is_explained() -> None:
    # generate.py refuses to write fixtures otherwise; this catches a
    # hand-edited agreement.txt.
    for row in oracle_data.rows("agreement.txt"):
        check, compared, identical, explained = row
        counted = sum(int(item.split("=")[1]) for item in explained.split())
        assert int(identical) + counted == int(compared), check


def test_attack_ids_are_unique() -> None:
    ids = [attack.id for attack in ATTACKS]
    assert len(ids) == len(set(ids))


def test_every_attack_is_in_the_corpus() -> None:
    corpus = {case.text for case in oracle_data.strings()}
    missing = [attack.id for attack in ATTACKS if attack.text not in corpus]
    assert missing == []


def test_attacks_marked_confusable_are_confusable() -> None:
    classes = {(case.a, case.b): case.confusable for case in oracle_data.pairs()}
    wrong = [
        attack.id
        for attack in ATTACKS
        if attack.confusable_with is not None
        and not classes[(attack.text, attack.confusable_with)]
    ]
    assert wrong == []


def test_skeleton_data_is_idempotent() -> None:
    # UTS #39 section 4: internalSkeleton(internalSkeleton(X)) equals
    # internalSkeleton(X), so every character a skeleton produces must be its
    # own skeleton.
    skeletons = oracle_data.skeletons()
    produced = {c for value in skeletons.values() for c in value}
    not_fixed = sorted(f"U+{ord(c):04X}" for c in produced if skeletons.get(c, c) != c)
    assert not_fixed == []


def test_rtl_skeleton_is_skeleton_of_mirror_glyph() -> None:
    # A lone mirrored character in a right-to-left paragraph displays as its
    # Bidi_Mirroring_Glyph, so its RTL bidiSkeleton is that glyph's skeleton.
    mirror = oracle_data.properties()["Bidi_Mirroring_Glyph"]
    skeletons = oracle_data.skeletons()
    for c, rtl in oracle_data.rtl_skeletons().items():
        glyph = chr(int(mirror(ord(c)), 16))
        assert rtl == skeletons.get(glyph, glyph), f"U+{ord(c):04X}"


def test_default_ignorables_have_empty_skeletons() -> None:
    # UTS #39 internalSkeleton step 2 removes them.
    ignorable = oracle_data.properties()["Default_Ignorable_Code_Point"]
    skeletons = oracle_data.skeletons()
    for cp in ignorable.values:
        if not 0xD800 <= cp <= 0xDFFF:
            assert skeletons.get(chr(cp)) == "", f"U+{cp:04X}"


def test_string_rows_are_well_formed() -> None:
    levels = {
        "ASCII_ONLY",
        "SINGLE_SCRIPT",
        "HIGHLY_RESTRICTIVE",
        "MODERATELY_RESTRICTIVE",
        "MINIMALLY_RESTRICTIVE",
        "UNRESTRICTED",
    }
    checks = {"CHAR_LIMIT", "INVISIBLE", "MIXED_NUMBERS", "HIDDEN_OVERLAY"}
    for case in oracle_data.strings():
        assert case.restriction_level in levels
        assert case.failed_checks <= checks
        assert case.grapheme_boundaries[0] == 0
        assert case.grapheme_boundaries[-1] == len(case.text)
        # Profile violations and the Unrestricted level are the same test.
        assert ("CHAR_LIMIT" in case.failed_checks) == (
            case.restriction_level == "UNRESTRICTED"
        )


def test_grapheme_break_tests_parse() -> None:
    cases = oracle_data.grapheme_break_tests()
    path = oracle_data.FIXTURES / "GraphemeBreakTest.txt"
    with path.open(encoding="utf-8") as lines:
        assert len(cases) == sum(line.startswith("÷") for line in lines)
    for case in cases:
        assert case.boundaries[0] == 0
        assert case.boundaries[-1] == len(case.text)
