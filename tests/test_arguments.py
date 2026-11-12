"""What the public functions take: str, and nothing else.

The functions take str, as unicodedata's do, and raise TypeError for
anything else, bytes included: an ASCII fast path once answered for ASCII
bytes. A str can also hold lone surrogates, which are not Unicode text. The
functions accept them, as unicodedata does, and answer from their properties
(General_Category Cs, Identifier_Status Restricted); docs/accepting-names.md
refuses text that does not encode as UTF-8 before the checks.
"""

from collections.abc import Callable
from typing import Any

import pytest

import confusable

# Every public function that takes text, called with one argument changed.
# The argument is Any because the tests pass what the signatures forbid.
TEXT_FUNCTIONS: dict[str, Callable[[Any], object]] = {
    "skeleton": confusable.skeleton,
    "match": lambda x: confusable.match(x, "a"),
    "match, argument 2": lambda x: confusable.match("a", x),
    "restriction_level": confusable.restriction_level,
    "is_mixed_script": confusable.is_mixed_script,
    "is_allowed": confusable.is_allowed,
    "has_mixed_numbers": confusable.has_mixed_numbers,
    "has_unlikely_marks": confusable.has_unlikely_marks,
    "has_hidden_overlay": confusable.has_hidden_overlay,
    "find_invisible": confusable.find_invisible,
    "has_invisible": confusable.has_invisible,
    "iter_graphemes": lambda x: [str(g) for g in confusable.iter_graphemes(x)],
    "truncate": lambda x: confusable.truncate(x, 5),
}
CHAR_FUNCTIONS: dict[str, Callable[[Any], object]] = {
    "identifier_status": confusable.identifier_status,
    "identifier_types": confusable.identifier_types,
    "isxidstart": confusable.isxidstart,
    "isxidcontinue": confusable.isxidcontinue,
}
NOT_TEXT = [None, b"abc", b"", bytearray(b"abc"), memoryview(b"abc"), 1, ["a"]]


def test_every_public_function_is_covered() -> None:
    public = {
        name
        for name in confusable.__all__
        if callable(getattr(confusable, name))
        and not isinstance(getattr(confusable, name), type)
    }
    covered = {name.split(",")[0] for name in TEXT_FUNCTIONS} | set(CHAR_FUNCTIONS)
    assert covered == public


@pytest.mark.parametrize("name", sorted(TEXT_FUNCTIONS))
@pytest.mark.parametrize("value", NOT_TEXT, ids=repr)
def test_text_functions_take_only_str(name: str, value: object) -> None:
    function = name.split(",")[0]
    position = 2 if name.endswith("argument 2") else 1
    message = (
        f"{function}() argument {position} must be str, not {type(value).__name__}"
    )
    with pytest.raises(TypeError) as raised:
        TEXT_FUNCTIONS[name](value)
    assert str(raised.value) == message


@pytest.mark.parametrize("name", sorted(CHAR_FUNCTIONS))
@pytest.mark.parametrize("value", [*NOT_TEXT, "", "ab"], ids=repr)
def test_character_functions_take_one_character(name: str, value: object) -> None:
    with pytest.raises(TypeError):
        CHAR_FUNCTIONS[name](value)


class Name(str):
    pass


@pytest.mark.parametrize("name", sorted(TEXT_FUNCTIONS))
def test_a_str_subclass_is_text(name: str) -> None:
    result = TEXT_FUNCTIONS[name](Name("p\u0430ypal"))
    assert result == TEXT_FUNCTIONS[name]("p\u0430ypal")


def test_lone_surrogates_are_accepted_and_restricted() -> None:
    for text in ("\ud800", "a\udc00b", "\udfff\ud800"):
        assert not confusable.is_allowed(text)
        assert confusable.restriction_level(text) is (
            confusable.RestrictionLevel.UNRESTRICTED
        )
        assert confusable.skeleton(text) == text
        assert confusable.find_invisible(text) == []
        assert not confusable.has_invisible(text)
        assert confusable.truncate(text, 5) == text
    assert confusable.identifier_status("\ud800") is (
        confusable.IdentifierStatus.RESTRICTED
    )
    assert confusable.identifier_types("\ud800") == frozenset(
        {confusable.IdentifierType.NOT_CHARACTER}
    )
    # Two surrogates are not a pair here: each is a cluster of its own.
    assert [str(s) for s in confusable.iter_graphemes("\ud800\udc00")] == [
        "\ud800",
        "\udc00",
    ]
