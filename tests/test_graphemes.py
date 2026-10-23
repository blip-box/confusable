"""iter_graphemes(), Segment and truncate() beyond the conformance fixtures."""

import sys
import unicodedata

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from confusable import Segment, iter_graphemes, truncate
from confusable._graphemes import _BREAK, _CONJUNCT, _PICTOGRAPHIC

FAMILY = "\U0001f468\u200d\U0001f469\u200d\U0001f467"  # one cluster
FLAG_US = "\U0001f1fa\U0001f1f8"
TEXT = "e\u0301xy" + FLAG_US


def spans(*args: object) -> list[tuple[int, int, str]]:
    return [(g.start, g.end, str(g)) for g in iter_graphemes(*args)]  # type: ignore[arg-type]


def test_segments() -> None:
    first = next(iter_graphemes(TEXT))
    assert isinstance(first, Segment)
    assert (first.start, first.end, str(first)) == (0, 2, "e\u0301")
    assert repr(first) == "<Segment 0:2>"
    with pytest.raises(AttributeError):
        first.start = 1  # type: ignore[misc]
    iterator = iter_graphemes(TEXT)
    assert iter(iterator) is iterator


# What Python 3.15's unicodedata.iter_graphemes does with start and end: it
# segments text[start:end], as in a slice, as a string of its own.
@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((), [(0, 2, "e\u0301"), (2, 3, "x"), (3, 4, "y"), (4, 6, FLAG_US)]),
        ((1,), [(1, 2, "\u0301"), (2, 3, "x"), (3, 4, "y"), (4, 6, FLAG_US)]),
        ((0, 1), [(0, 1, "e")]),
        ((2, 4), [(2, 3, "x"), (3, 4, "y")]),
        ((-2,), [(4, 6, FLAG_US)]),
        ((0, -1), [(0, 2, "e\u0301"), (2, 3, "x"), (3, 4, "y"), (4, 5, FLAG_US[0])]),
        ((10,), []),
        ((5,), [(5, 6, FLAG_US[1])]),
        ((4, 2), []),
    ],
)
def test_start_and_end_select_a_slice(
    args: tuple[int, ...], expected: list[tuple[int, int, str]]
) -> None:
    assert spans(TEXT, *args) == expected


def test_bad_arguments_fail_at_the_call() -> None:
    with pytest.raises(TypeError):
        iter_graphemes(b"abc")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        iter_graphemes("abc", "1")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "clusters"),
    [
        ("", []),
        ("a\r\nb", ["a", "\r\n", "b"]),  # GB3
        ("\n\r", ["\n", "\r"]),
        ("\u1100\u0301", ["\u1100\u0301"]),  # a Hangul L, then an accent (GB9)
        ("\u1100\u1161\u11a8", ["\u1100\u1161\u11a8"]),  # GB6, GB7
        (FAMILY + "!", [FAMILY, "!"]),  # GB11
        (FLAG_US * 2 + FLAG_US[0], [FLAG_US, FLAG_US, FLAG_US[0]]),  # GB12, GB13
        # GB9c in revision 49: Linker Extend* x Consonant, with no consonant
        # needed before the linker. Devanagari KA, VIRAMA, ZWJ, SSA.
        ("\u0915\u094d\u200d\u0937", ["\u0915\u094d\u200d\u0937"]),
        ("\u094d\u0937", ["\u094d\u0937"]),
    ],
)
def test_clusters(text: str, clusters: list[str]) -> None:
    assert [str(g) for g in iter_graphemes(text)] == clusters


@given(st.text())
def test_segments_cover_the_text(text: str) -> None:
    segments = list(iter_graphemes(text))
    assert "".join(map(str, segments)) == text
    assert all(g.start < g.end for g in segments)
    assert [g.start for g in segments[1:]] == [g.end for g in segments[:-1]]


@given(st.text(st.characters(max_codepoint=0x7F)))
def test_ascii_fast_path(text: str) -> None:
    # A trailing non-ASCII letter sends the text down the general path, and
    # every rule breaks before it here.
    general = [g.end for g in iter_graphemes(text + "\u00e9")][:-1]
    assert [g.end for g in iter_graphemes(text)] == general


def _same_properties(c: str) -> bool:
    """Whether c has the same grapheme properties in Python's Unicode data."""
    cp = ord(c)
    return bool(
        unicodedata.grapheme_cluster_break(c) == _BREAK[cp]  # type: ignore[attr-defined]
        and unicodedata.indic_conjunct_break(c) == _CONJUNCT[cp]  # type: ignore[attr-defined]
        and unicodedata.extended_pictographic(c) == (cp in _PICTOGRAPHIC)  # type: ignore[attr-defined]
    )


# One or more characters of each kind the rules treat specially: controls,
# Hangul jamo and syllables, marks, ZWJ, prepends, regional indicators,
# pictographs and Indic consonants.
SPECIAL = st.sampled_from(
    list(
        "\r\n\x00\u0301\u200d\u0903\u0600\U0001f1fa\U0001f1f8\U0001f468"
        "\U0001f3fb\ufe0f\u1100\u1161\u11a8\uac00\uac01\u0915\u0937\u093c"
    )
)


@pytest.mark.skipif(sys.version_info < (3, 15), reason="unicodedata.iter_graphemes")
@given(st.text(st.one_of(st.characters(), SPECIAL)))
def test_same_as_python_where_the_unicode_versions_agree(text: str) -> None:
    # Python 3.15 implements Unicode 17, which segments text the same way
    # except for the new GB9c and characters whose properties changed.
    assume(all(_same_properties(c) for c in text))
    assume(all(_CONJUNCT[ord(c)] != "Linker" for c in text))
    python = [(g.start, g.end) for g in unicodedata.iter_graphemes(text)]  # type: ignore[attr-defined]
    assert [(g.start, g.end) for g in iter_graphemes(text)] == python


def test_truncate_needs_a_limit() -> None:
    with pytest.raises(TypeError):
        truncate("abc")
    with pytest.raises(ValueError, match="negative"):
        truncate("abc", -1)


CAFE = "cafe\u0301 cr\u00e8me"  # with a combining acute, then a precomposed grave


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"max_graphemes": 4}, "cafe\u0301"),
        ({"max_graphemes": 0}, ""),
        ({"max_graphemes": 100}, CAFE),
        ({"max_code_points": 4}, "caf"),  # the e and its accent are two
        ({"max_code_points": 5}, "cafe\u0301"),
        ({"max_utf8_bytes": 5}, "caf"),  # e + U+0301 is three bytes
        ({"max_utf8_bytes": 6}, "cafe\u0301"),
        ({"max_graphemes": 10, "max_utf8_bytes": 9}, "cafe\u0301 cr"),
        ({"max_utf16_units": 6}, "cafe\u0301 "),
    ],
)
def test_truncate(kwargs: dict[str, int], expected: str) -> None:
    assert truncate(CAFE, **kwargs) == expected


def test_truncate_keeps_clusters_whole() -> None:
    assert truncate(FAMILY + "x", max_code_points=4) == ""
    assert truncate(FAMILY + "x", 1) == FAMILY
    assert truncate(FLAG_US * 2, max_utf16_units=7) == FLAG_US
    assert truncate("a\r\nb", max_code_points=2) == "a"
    zalgo = "a" + "\u0300\u0301\u0302\u0303" * 50  # one cluster of 201 code points
    assert truncate(zalgo, 300) == zalgo
    assert truncate(zalgo, 300, max_utf8_bytes=300) == ""


def _sizes(text: str) -> tuple[int, int, int, int]:
    return (
        len(list(iter_graphemes(text))),
        len(text),
        len(text.encode("utf-8", "surrogatepass")),
        len(text.encode("utf-16-le", "surrogatepass")) // 2,
    )


limit = st.one_of(st.none(), st.integers(0, 20))


@given(st.text(), st.tuples(limit, limit, limit, limit))
def test_truncate_keeps_the_longest_fitting_prefix(
    text: str, limits: tuple[int | None, int | None, int | None, int | None]
) -> None:
    assume(any(value is not None for value in limits))
    graphemes, code_points, utf8, utf16 = limits
    result = truncate(
        text,
        graphemes,
        max_code_points=code_points,
        max_utf8_bytes=utf8,
        max_utf16_units=utf16,
    )
    assert text.startswith(result)
    ends = [0, *(g.end for g in iter_graphemes(text))]
    assert len(result) in ends

    def fits(prefix: str) -> bool:
        return all(
            value is None or size <= value
            for size, value in zip(_sizes(prefix), limits, strict=True)
        )

    assert fits(result)
    if result != text:
        assert not fits(text[: ends[ends.index(len(result)) + 1]])
