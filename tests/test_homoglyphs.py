"""confusable.compat.homoglyphs against confusable_homoglyphs 3.3.1.

The fixtures come from the real package (tools/oracles/homoglyphs/oracle.py):
the data its own generator makes from the pinned Unicode files, and its
functions' results on corrected data.
"""

from typing import Any

import pytest

from confusable._data.homoglyphs import NAMES, PAIRS
from confusable.compat.homoglyphs import categories, confusables
from tests.conformance import oracle_data

LRM = "\u200e"  # LEFT-TO-RIGHT MARK

# The confusables.txt lines whose comment the package's generator cannot read:
# their characters show as blanks. LINE SEPARATOR, PARAGRAPH SEPARATOR, HANGUL
# FILLER and HALFWIDTH HANGUL FILLER.
UNPARSED = {"\u2028", "\u2029", "\u3164", "\uffa0"}


def unwrap(text: str) -> str:
    """Remove the LEFT-TO-RIGHT MARKs the generator copies from comments."""
    if len(text) > 2 and text[0] == LRM and text[-1] == LRM:
        return text[1:-1]
    return text


def test_categories_data_is_its_generators() -> None:
    assert categories.categories_data == oracle_data.homoglyph_data()["categories"]


def test_confusables_data_is_its_generators_but_for_two_bugs() -> None:
    generated = oracle_data.homoglyph_data()["confusables"]
    # The first bug: right-to-left characters are stored inside LRMs, so a
    # lookup of the character itself finds nothing.
    assert "\u0627" not in generated  # ARABIC LETTER ALEF
    assert LRM + "\u0627" + LRM in generated
    unwrapped = {
        unwrap(key): [{"c": unwrap(h["c"]), "n": h["n"]} for h in homoglyphs]
        for key, homoglyphs in generated.items()
    }
    assert len(unwrapped) == len(generated)
    # The second: the lines with blank-looking characters are missing.
    expected: dict[str, list[dict[str, str]]] = {}
    for source, target in PAIRS:
        if source in UNPARSED:
            continue
        expected.setdefault(source, []).append({"c": target, "n": NAMES[target]})
        expected.setdefault(target, []).append({"c": source, "n": NAMES[source]})
    assert unwrapped == expected
    # Also missing: U+1160 HANGUL JUNGSEONG FILLER, the target of two of them.
    missing = set(confusables.confusables_data) - set(expected)
    assert missing == {*UNPARSED, "\u1160"}


def summary(found: Any) -> Any:
    """The fixture's form of an is_confusable result."""
    if found is False:
        return False
    return [[f["character"], f["alias"], len(f["homoglyphs"])] for f in found]


def test_functions_return_what_the_package_returns() -> None:
    mismatches = []
    for case in oracle_data.homoglyph_cases():
        s = case.text
        got = (
            sorted(categories.unique_aliases(s)),
            tuple(
                confusables.is_mixed_script(s, *([] if a is None else [a]))
                for a in oracle_data.HOMOGLYPH_ALLOWED
            ),
            tuple(
                confusables.is_dangerous(s, preferred_aliases=p)
                for p in oracle_data.HOMOGLYPH_DANGEROUS
            ),
            [
                summary(confusables.is_confusable(s, greedy=True, preferred_aliases=p))
                for p in oracle_data.HOMOGLYPH_PREFERRED
            ],
        )
        expected = (case.unique_aliases, case.mixed, case.dangerous, case.confusable)
        if got != expected:
            mismatches.append(oracle_data.hex_seq(s))
        # Without greedy, the search stops at the first character found.
        for preferred, everything in zip(
            oracle_data.HOMOGLYPH_PREFERRED, case.confusable, strict=True
        ):
            first = summary(confusables.is_confusable(s, preferred_aliases=preferred))
            if first != (everything and everything[:1]):
                mismatches.append(f"{oracle_data.hex_seq(s)} not greedy")
    assert not mismatches, mismatches[:20]


def test_result_shapes() -> None:
    found = confusables.is_confusable("\u03c1\u03c4\u03c4p")  # GREEK RHO, TAU, TAU, p
    assert found is not False
    assert found == [
        {
            "character": "\u03c1",
            "alias": "GREEK",
            "homoglyphs": [{"c": "p", "n": "LATIN SMALL LETTER P"}],
        }
    ]
    assert list(found[0]) == ["character", "alias", "homoglyphs"]
    # Results are copies: changing one leaves the data alone.
    found[0]["homoglyphs"].clear()
    assert confusables.is_confusable("\u03c1")


@pytest.mark.parametrize(
    ("text", "preferred", "character"),
    [
        ("g\u0647", ["latin"], "\u0647"),  # ARABIC LETTER HEH looks like o
        ("l\u05d5l", ["latin"], "\u05d5"),  # HEBREW LETTER VAV looks like l
        # HANGUL FILLER, missing from the package's data. It looks like U+1160
        # HANGUL JUNGSEONG FILLER, not like anything Latin.
        ("name\u3164", [], "\u3164"),
    ],
)
def test_finds_what_the_package_misses(
    text: str, preferred: list[str], character: str
) -> None:
    found = confusables.is_confusable(text, greedy=True, preferred_aliases=preferred)
    assert found is not False
    assert character in [f["character"] for f in found]


def test_categories() -> None:
    assert categories.aliases_categories("A") == ("LATIN", "L")
    assert categories.aliases_categories("-") == ("COMMON", "Pd")
    assert categories.alias("\u03c4") == "GREEK"
    assert categories.category("\u0301") == "Mn"
    assert categories.aliases_categories("\u0378") == ("Unknown", "Zzzz")  # unassigned
    assert categories.aliases_categories(chr=" ") == ("COMMON", "Zs")


def test_every_code_point_has_its_generators_category() -> None:
    data = oracle_data.homoglyph_data()["categories"]
    expected = {}
    for first, last, a, c in data["code_points_ranges"]:
        for cp in range(first, last + 1):
            expected[cp] = (data["iso_15924_aliases"][a], data["categories"][c])
    for cp in range(0x110000):
        assert categories.aliases_categories(chr(cp)) == expected.get(
            cp, ("Unknown", "Zzzz")
        ), hex(cp)


def test_unknown_attributes() -> None:
    with pytest.raises(AttributeError):
        _ = categories.no_such_thing
    with pytest.raises(AttributeError):
        _ = confusables.no_such_thing
