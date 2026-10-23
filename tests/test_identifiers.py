"""The identifier API beyond what the conformance fixtures pin."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from confusable import (
    IdentifierStatus,
    IdentifierType,
    identifier_status,
    identifier_types,
    is_allowed,
    isxidcontinue,
    isxidstart,
)
from confusable._normalize import nfc, nfd

# Latin and Arabic letters with combining marks, some Allowed only composed
# (U+032D, U+0653) and some only decomposed (U+0306 on E).
canonical_text = st.text(
    st.sampled_from("EDAa\u0627\u0306\u0308\u032d\u0653\u0114\u1e12\u0622")
)


@given(st.one_of(st.text(), canonical_text))
def test_is_allowed_does_not_depend_on_the_encoding(text: str) -> None:
    assert is_allowed(text) == is_allowed(nfd(text)) == is_allowed(nfc(text))


@pytest.mark.parametrize(
    ("text", "allowed"),
    [
        ("", True),
        ("paypal", True),
        ("pay pal", False),
        ("\u0114", True),  # Restricted itself; E + U+0306 is Allowed
        ("\u0627\u0653", True),  # U+0653 is Restricted; U+0622 is Allowed
        ("a\u200d", False),  # ZERO WIDTH JOINER
    ],
)
def test_is_allowed(text: str, allowed: bool) -> None:
    assert is_allowed(text) is allowed


def test_identifier_status_and_types() -> None:
    assert identifier_status("a") is IdentifierStatus.ALLOWED
    assert identifier_types("a") == {IdentifierType.RECOMMENDED}
    assert identifier_status("\u0114") is IdentifierStatus.RESTRICTED
    assert identifier_types("\u0114") == {IdentifierType.UNCOMMON_USE}
    assert identifier_types("\ue000") == {IdentifierType.NOT_CHARACTER}


@pytest.mark.parametrize(
    ("char", "start", "continue_"),
    [("a", True, True), ("_", False, True), ("1", False, True), ("-", False, False)],
)
def test_xid(char: str, start: bool, continue_: bool) -> None:
    assert isxidstart(char) is start
    assert isxidcontinue(char) is continue_


@pytest.mark.parametrize(
    "function", [identifier_status, identifier_types, isxidstart, isxidcontinue]
)
@pytest.mark.parametrize("value", ["", "ab"])
def test_character_functions_take_one_character(function: object, value: str) -> None:
    with pytest.raises(TypeError, match="single character"):
        function(value)  # type: ignore[operator]
