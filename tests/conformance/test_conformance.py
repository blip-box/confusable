"""The library against the oracle fixtures.

Every test reaches the library through adapter.py. Until the library
implements an operation, the adapter raises NotImplementedYetError and the test is
a strict xfail: a wrong answer fails as usual, and a right answer fails too
until the marker is removed, so the markers track what is implemented.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.conformance import adapter, oracle_data

DIRECTIONS: tuple[Literal["LTR", "RTL"], ...] = ("LTR", "RTL")
SKELETONS: tuple[Literal["skeleton", "internal", "rtl"], ...] = (
    "skeleton",
    "internal",
    "rtl",
)


def not_implemented(operation: str) -> pytest.MarkDecorator:
    return pytest.mark.xfail(
        raises=adapter.NotImplementedYetError,
        strict=True,
        reason=f"confusable does not implement {operation} yet",
    )


def assert_all(mismatches: Iterable[str]) -> None:
    """Fail with the first mismatches listed, not just the first one."""
    found = list(mismatches)
    shown = "\n".join(found[:25])
    assert not found, f"{len(found)} mismatches; the first ones:\n{shown}"


def show(value: str) -> str:
    return oracle_data.hex_seq(value) or "<empty>"


# Skeletons and normalization.


def test_skeleton_of_every_code_point() -> None:
    expected = oracle_data.skeletons()
    assert_all(
        f"U+{cp:04X}: expected {show(expected.get(c, c))}, got {show(got)}"
        for cp in oracle_data.SCALAR_VALUES
        if (got := adapter.skeleton(c := chr(cp))) != expected.get(c, c)
    )


def test_rtl_bidi_skeleton_of_every_code_point() -> None:
    skeletons, rtl = oracle_data.skeletons(), oracle_data.rtl_skeletons()
    assert_all(
        f"U+{cp:04X}: got {show(got)}"
        for cp in oracle_data.SCALAR_VALUES
        if (got := adapter.bidi_skeleton(c := chr(cp), "RTL"))
        != rtl.get(c, skeletons.get(c, c))
    )


def test_nfd_of_every_code_point() -> None:
    expected = oracle_data.nfd()
    assert_all(
        f"U+{cp:04X}: got {show(got)}"
        for cp in oracle_data.SCALAR_VALUES
        if (got := adapter.nfd(c := chr(cp))) != expected.get(c, c)
    )


def test_skeleton_of_corpus_strings() -> None:
    assert_all(
        f"{show(case.text)}: expected {show(case.skeleton)}, got {show(got)}"
        for case in oracle_data.strings()
        if (got := adapter.skeleton(case.text)) != case.skeleton
    )


def test_internal_skeleton_of_corpus_strings() -> None:
    assert_all(
        f"{show(case.text)}: expected {show(case.internal_skeleton)}, got {show(got)}"
        for case in oracle_data.strings()
        if (got := adapter.internal_skeleton(case.text)) != case.internal_skeleton
    )


def test_bidi_skeletons_of_corpus_strings() -> None:
    assert_all(
        f"{show(case.text)} {direction}: expected {show(want)}, got {show(got)}"
        for case in oracle_data.strings()
        for direction, want in zip(
            DIRECTIONS, (case.skeleton, case.rtl_skeleton), strict=True
        )
        if (got := adapter.bidi_skeleton(case.text, direction)) != want
    )


def test_nfd_of_corpus_strings() -> None:
    assert_all(
        f"{show(case.text)}: expected {show(case.nfd)}, got {show(got)}"
        for case in oracle_data.strings()
        if (got := adapter.nfd(case.text)) != case.nfd
    )


def test_unicode_normalization_tests_nfc() -> None:
    # NormalizationTest.txt: c2 == NFC(c1) == NFC(c2) == NFC(c3), and
    # c4 == NFC(c4) == NFC(c5).
    assert_all(
        f"NormalizationTest.txt line {case.line}"
        for case in oracle_data.normalization_tests()
        if {adapter.nfc(c) for c in case.columns[:3]} != {case.columns[1]}
        or {adapter.nfc(c) for c in case.columns[3:]} != {case.columns[3]}
    )


def test_unicode_normalization_tests() -> None:
    # NormalizationTest.txt: c3 == NFD(c1) == NFD(c2) == NFD(c3), and
    # c5 == NFD(c4) == NFD(c5).
    assert_all(
        f"NormalizationTest.txt line {case.line}"
        for case in oracle_data.normalization_tests()
        if {adapter.nfd(c) for c in case.columns[:3]} != {case.columns[2]}
        or {adapter.nfd(c) for c in case.columns[3:]} != {case.columns[4]}
    )


# Confusable classes.


def test_confusable_classes_of_corpus_pairs() -> None:
    assert_all(
        f"{show(case.a)} / {show(case.b)} ({kind}): "
        f"expected {sorted(want)}, got {sorted(got)}"
        for case in oracle_data.pairs()
        for kind, want in zip(
            SKELETONS, (case.confusable, case.internal, case.rtl), strict=True
        )
        if (got := adapter.confusable_classes(case.a, case.b, kind)) != want
    )


# Mixed scripts, restriction levels and the optional checks.


def test_resolved_script_sets() -> None:
    assert_all(
        f"{show(case.text)}: expected {case.resolved_script_set!r}, got {got!r}"
        for case in oracle_data.strings()
        if (got := adapter.resolved_script_set(case.text)) != case.resolved_script_set
    )


def test_restriction_levels() -> None:
    assert_all(
        f"{show(case.text)}: expected {case.restriction_level}, got {got}"
        for case in oracle_data.strings()
        if (got := adapter.restriction_level(case.text)) != case.restriction_level
    )


def test_outside_profile() -> None:
    assert_all(
        show(case.text)
        for case in oracle_data.strings()
        if adapter.outside_profile(case.text) != ("CHAR_LIMIT" in case.failed_checks)
    )


@not_implemented("repeated_nonspacing_mark")
def test_repeated_nonspacing_marks() -> None:
    assert_all(
        show(case.text)
        for case in oracle_data.strings()
        if adapter.repeated_nonspacing_mark(case.text)
        != ("INVISIBLE" in case.failed_checks)
    )


@not_implemented("hidden_overlay")
def test_hidden_overlays() -> None:
    assert_all(
        show(case.text)
        for case in oracle_data.strings()
        if adapter.hidden_overlay(case.text) != ("HIDDEN_OVERLAY" in case.failed_checks)
    )


@not_implemented("decimal_zeros")
def test_decimal_zeros() -> None:
    assert_all(
        f"{show(case.text)}: expected {sorted(case.decimal_zeros)}, got {sorted(got)}"
        for case in oracle_data.strings()
        if (got := adapter.decimal_zeros(case.text)) != case.decimal_zeros
    )


# Grapheme clusters.


@not_implemented("grapheme_boundaries")
def test_unicode_grapheme_break_tests() -> None:
    assert_all(
        f"GraphemeBreakTest.txt line {case.line}: expected {case.boundaries}, got {got}"
        for case in oracle_data.grapheme_break_tests()
        if (got := adapter.grapheme_boundaries(case.text)) != case.boundaries
    )


@not_implemented("grapheme_boundaries")
def test_grapheme_boundaries_of_corpus_strings() -> None:
    assert_all(
        f"{show(case.text)}: expected {case.grapheme_boundaries}, got {got}"
        for case in oracle_data.strings()
        if (got := adapter.grapheme_boundaries(case.text)) != case.grapheme_boundaries
    )


# The Unicode Bidirectional Algorithm, which bidiSkeleton applies.


def test_unicode_bidi_character_tests() -> None:
    assert_all(
        f"BidiCharacterTest.txt line {case.line}: got {got}"
        for case in oracle_data.bidi_character_tests()
        if (got := adapter.bidi_paragraph(case.text, case.direction))
        != (case.paragraph_level, case.levels, case.order)
    )


def test_unicode_bidi_tests() -> None:
    assert_all(
        f"BidiTest.txt line {case.line} ({case.direction}): got {got}"
        for case in oracle_data.bidi_tests()
        if (got := adapter.bidi_classes(case.classes, case.direction))
        != (case.levels, case.order)
    )


def test_bidi_display_of_corpus_strings() -> None:
    assert_all(
        f"{show(case.text)} {direction}: expected {show(want)}, got {show(got)}"
        for case in oracle_data.strings()
        for direction, want in zip(
            DIRECTIONS, (case.display_ltr, case.display_rtl), strict=True
        )
        if (got := adapter.bidi_display(case.text, direction)) != want
    )


# Only R, AL, AN, RLE, RLO and RLI can put text at an odd level in a
# left-to-right paragraph, so without them display order is the identity.
# UTS #39 section 4 states this fast path with only R and AL, which is wrong:
# RLO reverses the Latin in "invoice\u202egpj.exe", and a neutral between two
# Arabic-Indic digits (AN) resolves to R and is mirrored.
_ODD_LEVEL_CLASSES = {"R", "AL", "AN", "RLE", "RLO", "RLI"}
_bidi_class = oracle_data.properties()["Bidi_Class"]


@given(
    st.text(
        st.characters().filter(lambda c: _bidi_class(ord(c)) not in _ODD_LEVEL_CLASSES)
    )
)
def test_left_to_right_display_without_odd_level_classes_is_identity(text: str) -> None:
    assert adapter.bidi_display(text, "LTR") == text


def test_uts39_fast_path_needs_more_than_r_and_al() -> None:
    for text in ("invoice\u202egpj.exe", "\u0661(\u0662", "\u202ba!\u202c"):
        assert not {_bidi_class(ord(c)) for c in text} & {"R", "AL"}
        assert adapter.bidi_display(text, "LTR") != text


# Character properties, for the generated data tables.


@pytest.mark.parametrize("name", sorted(oracle_data.properties()))
def test_property_of_every_code_point(name: str) -> None:
    expected = oracle_data.properties()[name]
    assert_all(
        f"U+{cp:04X}: expected {expected(cp)!r}, got {got!r}"
        for cp in range(0x110000)
        if (got := adapter.property_value(name, cp)) != expected(cp)
    )


# Properties the specifications guarantee for every input.


@given(st.text())
def test_internal_skeleton_is_idempotent(text: str) -> None:
    once = adapter.internal_skeleton(text)
    assert adapter.internal_skeleton(once) == once


@given(st.text())
def test_internal_skeleton_ignores_normalization(text: str) -> None:
    normalized = adapter.nfd(text)
    assert adapter.internal_skeleton(normalized) == adapter.internal_skeleton(text)


@given(st.text(), st.text())
def test_confusability_is_symmetric(a: str, b: str) -> None:
    assert adapter.confusable_classes(a, b) == adapter.confusable_classes(b, a)


@given(st.text())
def test_every_string_is_confusable_with_itself(text: str) -> None:
    assert adapter.confusable_classes(text, text)
