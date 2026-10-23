"""find_invisible() and has_invisible(): invisible and control characters."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from confusable import Invisible, find_invisible, has_invisible
from confusable._data.properties import DEFAULT_IGNORABLE_RANGES, GENERAL_CATEGORY_RUNS
from confusable._invisible import CONTROL_RANGES
from confusable._normalize import nfc, nfd
from tests.conformance import oracle_data

CONTROL = Invisible.CONTROL
BIDI = Invisible.BIDI_CONTROL
JOIN = Invisible.JOIN_CONTROL
TAG = Invisible.TAG
VS = Invisible.VARIATION_SELECTOR
IGNORABLE = Invisible.DEFAULT_IGNORABLE


def tags(ascii_text: str) -> str:
    """ASCII text written in Tag characters, as ASCII smuggling hides it."""
    return "".join(chr(0xE0000 + ord(c)) for c in ascii_text)


ENGLAND = "\U0001f3f4" + tags("gbeng") + "\U000e007f"  # an RGI subdivision flag
TEXAS = "\U0001f3f4" + tags("ustx") + "\U000e007f"  # well formed, but not RGI
FAMILY = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
SINHALA = "\u0dc1\u0dca\u200d\u0dbb\u0dd3"  # UTS #39 section 3.1.1.1
PERSIAN = "\u0646\u0627\u0645\u0647\u200c\u0627\u06cc"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", []),
        ("paypal", []),
        # Controls.
        ("a\tb", [(1, CONTROL)]),
        ("\x1b[31mred", [(0, CONTROL)]),  # a terminal escape sequence
        ("x\x85", [(1, CONTROL)]),  # NEXT LINE, a C1 control
        # Bidirectional controls.
        ("invoice\u202egpj.exe", [(7, BIDI)]),
        ("\u2066x\u2069", [(0, BIDI), (2, BIDI)]),
        ("a\u200eb", [(1, BIDI)]),  # LEFT-TO-RIGHT MARK
        ("\u061c", [(0, BIDI)]),  # ARABIC LETTER MARK
        # Other characters that render as nothing.
        ("pay\u200bpal", [(3, IGNORABLE)]),  # ZERO WIDTH SPACE
        ("pay\u00adpal", [(3, IGNORABLE)]),  # SOFT HYPHEN
        ("pay\ufeffpal", [(3, IGNORABLE)]),  # ZERO WIDTH NO-BREAK SPACE
        ("\u3164", [(0, IGNORABLE)]),  # HANGUL FILLER, a blank "invisible name"
        ("a\u2065", [(1, IGNORABLE)]),  # unassigned, but default ignorable
        # Joining controls: visible only in some contexts.
        ("a\u200db", [(1, JOIN)]),
        ("a\u200cb", [(1, JOIN)]),
        (SINHALA, []),
        (PERSIAN, []),
        (FAMILY, []),
        ("\U0001f600\u200da", [(1, JOIN)]),  # an emoji, then a letter
        # Tags: only the RGI emoji tag sequences are visible.
        (ENGLAND, []),
        (
            "ok" + tags("ignore all previous instructions")[:6],
            [(i, TAG) for i in range(2, 8)],
        ),
        (TEXAS, [(i, TAG) for i in range(1, 6)]),
        ("\U000e007f", [(0, TAG)]),  # a lone CANCEL TAG
        (ENGLAND + tags("x"), [(7, TAG)]),
        # Variation selectors: only in a variation sequence, and one at a time.
        ("\u2764\ufe0f", []),  # emoji style
        ("\u2764\ufe0e", []),  # text style
        ("0\ufe00", []),  # a standardized variant: zero with a short stroke
        ("\u1820\u180b", []),  # MONGOLIAN LETTER A, FREE VARIATION SELECTOR ONE
        ("\u845b\U000e0100", []),  # an ideographic variation sequence
        ("a\ufe0f", [(1, VS)]),
        ("a\u180b", [(1, VS)]),
        ("\u2764\ufe0f\ufe0f", [(2, VS)]),
        ("\u845b\U000e0100\U000e0101", [(2, VS)]),
        ("\U0001f600\ufe0f", [(1, VS)]),  # already an emoji: no variation sequence
        # Bytes hidden in variation selectors after an emoji ("emoji smuggling").
        ("\U0001f600\U000e0158\U000e0159", [(1, VS), (2, VS)]),
    ],
)
def test_find_invisible(text: str, expected: list[tuple[int, Invisible]]) -> None:
    assert find_invisible(text) == expected
    assert has_invisible(text) is bool(expected)


def test_indexes_are_into_the_text_as_given() -> None:
    # NFC composes the jamo into one syllable, so the context is judged on a
    # shorter string; the indexes must still point into this one.
    text = "\u1100\u1161\u200b\u200d"
    assert nfc(text) == "\uac00\u200b\u200d"
    assert find_invisible(text) == [(2, IGNORABLE), (3, JOIN)]
    assert find_invisible("e\u0301\u200b") == [(2, IGNORABLE)]


def test_control_ranges_match_the_data() -> None:
    controls = []
    for n, (first, value) in enumerate(GENERAL_CATEGORY_RUNS):
        if value == "Cc":
            controls.append((first, GENERAL_CATEGORY_RUNS[n + 1][0] - 1))
    assert tuple(controls) == CONTROL_RANGES


def candidates() -> list[str]:
    ranges = (*CONTROL_RANGES, *DEFAULT_IGNORABLE_RANGES)
    return [chr(cp) for first, last in ranges for cp in range(first, last + 1)]


def test_every_candidate_alone_is_reported() -> None:
    every = candidates()
    # A space between them gives none of them a context.
    assert len(find_invisible(" ".join(every))) == len(every)


def test_nothing_else_is_reported() -> None:
    every = set(candidates())
    others = "".join(
        chr(cp)
        for cp in range(0x110000)
        if chr(cp) not in every and not 0xD800 <= cp <= 0xDFFF
    )
    assert find_invisible(others) == []


def test_every_rgi_emoji_sequence_is_visible() -> None:
    reported = [
        f"{oracle_data.hex_seq(sequence)} ({kind})"
        for sequence, kind in oracle_data.rgi_emoji_sequences()
        if find_invisible(sequence)
    ]
    assert not reported, reported[:20]


hidden_text = st.text(
    st.sampled_from(
        [
            *"ae0 ",
            *"\u0301\u0323\u00e9\u1100\u1161\u0915\u094d\u0628\u0627\u845b",
            *"\u200b\u200c\u200d\u202e\ufe0f\ufe00\u2764\x1b",
            "\U0001f468",
            "\U0001f3f4",
            "\U000e0067",
            "\U000e007f",
            "\U000e0100",
        ]
    ),
    max_size=12,
)


@given(hidden_text)
def test_kinds_ignore_normalization(text: str) -> None:
    def kinds(t: str) -> list[Invisible]:
        return [kind for _, kind in find_invisible(t)]

    assert kinds(text) == kinds(nfd(text)) == kinds(nfc(text))


@given(st.one_of(st.text(), hidden_text))
def test_has_invisible_agrees_with_find_invisible(text: str) -> None:
    assert has_invisible(text) is bool(find_invisible(text))
    for i, _ in find_invisible(text):
        assert 0 <= i < len(text)
