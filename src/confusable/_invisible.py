"""Invisible and control characters.

A character is reported if it renders as nothing (Default_Ignorable_Code_Point)
or is a C0 or C1 control (General_Category Cc), unless its context gives it a
visible job: ZWJ and ZWNJ in the contexts of UTS #39 section 3.1.1.1 or ZWJ
inside an emoji sequence, Tag characters inside an RGI emoji tag sequence (the
subdivision flags), and a variation selector that completes a variation
sequence.
"""

from __future__ import annotations

import enum
import re

from confusable import _joining
from confusable._data import emoji as _emoji
from confusable._data import graphemes as _graphemes
from confusable._data import properties as _properties
from confusable._data import variation as _variation
from confusable._lookup import Ranges, Runs
from confusable._normalize import nfc


class Invisible(enum.Enum):
    """Why find_invisible reports a character."""

    CONTROL = "control"
    """A C0 or C1 control character (General_Category Cc), such as ESC."""

    BIDI_CONTROL = "bidi-control"
    """A Bidi_Control character, which reorders the text it affects."""

    JOIN_CONTROL = "join-control"
    """ZWJ or ZWNJ where it does not change how the text looks."""

    TAG = "tag"
    """A Tag character outside an emoji tag sequence: hidden ASCII text."""

    VARIATION_SELECTOR = "variation-selector"
    """A variation selector that does not complete a variation sequence."""

    DEFAULT_IGNORABLE = "default-ignorable"
    """Any other Default_Ignorable_Code_Point, such as ZERO WIDTH SPACE."""


# General_Category Cc is immutable under the Unicode stability policy;
# tests/test_invisible.py checks these against the data anyway.
CONTROL_RANGES = ((0x0000, 0x001F), (0x007F, 0x009F))
_TAGS = range(0xE0000, 0xE0080)  # the Tags block
_IDEOGRAPHIC_SELECTORS = range(0xE0100, 0xE01F0)  # VARIATION SELECTOR-17 to -256

_BIDI_CONTROL = Ranges(_properties.BIDI_CONTROL_RANGES)
_VARIATION_SELECTOR = Ranges(_variation.VARIATION_SELECTOR_RANGES)
_UNIFIED_IDEOGRAPH = Ranges(_variation.UNIFIED_IDEOGRAPH_RANGES)
_EXTENDED_PICTOGRAPHIC = Ranges(_graphemes.EXTENDED_PICTOGRAPHIC_RANGES)
_GRAPHEME_BREAK = Runs(_graphemes.GRAPHEME_CLUSTER_BREAK_RUNS)

_CANDIDATES = re.compile(
    "["
    + "".join(
        f"{re.escape(chr(first))}-{re.escape(chr(last))}"
        for first, last in (*CONTROL_RANGES, *_properties.DEFAULT_IGNORABLE_RANGES)
    )
    + "]"
)


def _joins_emoji(text: str, i: int) -> bool:
    """Whether the ZWJ at i joins two emoji, as UAX #29 rule GB11 sees it.

    That is an Extended_Pictographic character, any Extend characters (such
    as a variation selector or a skin tone), ZWJ, and another
    Extended_Pictographic character: an emoji ZWJ sequence, which shows as
    one emoji where it is supported and as its parts elsewhere.
    """
    if i + 1 == len(text) or ord(text[i + 1]) not in _EXTENDED_PICTOGRAPHIC:
        return False
    before = i - 1
    while before >= 0 and _GRAPHEME_BREAK[ord(text[before])] == "Extend":
        before -= 1
    return before >= 0 and ord(text[before]) in _EXTENDED_PICTOGRAPHIC


def _completes_variation_sequence(text: str, i: int) -> bool:
    """Whether the variation selector at i follows a base it can vary.

    The pairs are the standardized and emoji variation sequences, and a
    selector from VARIATION SELECTOR-17 on after a unified ideograph, which
    UTS #37 defines as an ideographic variation sequence. Whether the
    Ideographic Variation Database registers that sequence is not checked.
    """
    if i == 0:
        return False
    base, selector = ord(text[i - 1]), ord(text[i])
    return (base, selector) in _variation.VARIATION_SEQUENCES or (
        selector in _IDEOGRAPHIC_SELECTORS and base in _UNIFIED_IDEOGRAPH
    )


def _tag_sequences(text: str) -> set[int]:
    """Return the positions of the Tag characters in RGI emoji tag sequences."""
    tagged: set[int] = set()
    for sequence in _emoji.RGI_EMOJI_TAG_SEQUENCES:
        start = text.find(sequence)
        while start != -1:
            tagged.update(range(start + 1, start + len(sequence)))
            start = text.find(sequence, start + len(sequence))
    return tagged


def _kind(text: str, i: int, tagged: set[int]) -> Invisible | None:
    cp = ord(text[i])
    if cp <= 0x9F:  # the only candidates below U+00AD are controls
        return Invisible.CONTROL
    if cp in _BIDI_CONTROL:
        return Invisible.BIDI_CONTROL
    if text[i] in _joining.JOINERS:
        if _joining.in_context(text, i) or (
            text[i] == _joining.ZWJ and _joins_emoji(text, i)
        ):
            return None
        return Invisible.JOIN_CONTROL
    if cp in _TAGS:
        return None if i in tagged else Invisible.TAG
    if cp in _VARIATION_SELECTOR:
        if _completes_variation_sequence(text, i):
            return None
        return Invisible.VARIATION_SELECTOR
    return Invisible.DEFAULT_IGNORABLE


def _needs_context(c: str) -> bool:
    cp = ord(c)
    return c in _joining.JOINERS or cp in _TAGS or cp in _VARIATION_SELECTOR


def find_invisible(text: str) -> list[tuple[int, Invisible]]:
    r"""Return the index and kind of each invisible or control character.

    Reported: C0 and C1 controls, bidirectional controls ("Trojan Source"),
    Tag characters (hidden ASCII, "ASCII smuggling"), and every other
    character that renders as nothing (Default_Ignorable_Code_Point), such as
    ZERO WIDTH SPACE, SOFT HYPHEN and HANGUL FILLER. Not reported where they
    have a visible job: ZWJ and ZWNJ in the contexts of UTS #39 section
    3.1.1.1 or ZWJ joining two emoji, Tag characters in an RGI emoji tag
    sequence such as the flag of England, and a variation selector that
    completes a variation sequence. A run of variation selectors after one
    base, which can hide data too, is reported from the second selector on.

    Contexts are judged on the NFC form of the text, so the result does not
    depend on how the text is encoded. Indexes are into text as given.

    >>> find_invisible("pay\u200bpal")  # ZERO WIDTH SPACE
    [(3, <Invisible.DEFAULT_IGNORABLE: 'default-ignorable'>)]
    >>> find_invisible("invoice\u202egpj.exe")  # RIGHT-TO-LEFT OVERRIDE
    [(7, <Invisible.BIDI_CONTROL: 'bidi-control'>)]
    >>> find_invisible("hi\U000e0068\U000e0069")  # "hi" again, in Tag characters
    [(2, <Invisible.TAG: 'tag'>), (3, <Invisible.TAG: 'tag'>)]
    >>> find_invisible("\u2764\ufe0f \U0001f469\u200d\U0001f4bb")  # emoji
    []
    """
    found = [match.start() for match in _CANDIDATES.finditer(text)]
    if not found:
        return []
    if any(_needs_context(text[i]) for i in found):
        # Normalization never adds, removes or moves a candidate, so the n-th
        # candidate of the NFC form is the n-th of the text.
        composed = nfc(text)
        at = [match.start() for match in _CANDIDATES.finditer(composed)]
    else:
        composed, at = text, found
    tagged = (
        _tag_sequences(composed) if any(ord(text[i]) in _TAGS for i in found) else set()
    )
    out = []
    for i, j in zip(found, at, strict=True):
        kind = _kind(composed, j, tagged)
        if kind is not None:
            out.append((i, kind))
    return out


def has_invisible(text: str) -> bool:
    r"""Return whether find_invisible reports any character of text.

    >>> has_invisible("paypal"), has_invisible("pay\u00adpal")  # SOFT HYPHEN
    (False, True)
    """
    if text.isascii():
        return not text.isprintable()  # only the controls
    return bool(find_invisible(text))
