import doctest

import pytest

from confusable import (
    _graphemes,
    _identifiers,
    _invisible,
    _marks,
    _numbers,
    _restriction,
    _skeleton,
)
from confusable.compat.homoglyphs import categories, confusables


@pytest.mark.parametrize(
    "module",
    [
        _graphemes,
        _identifiers,
        _invisible,
        _marks,
        _numbers,
        _restriction,
        _skeleton,
        categories,
        confusables,
    ],
)
def test_docstring_examples(module: object) -> None:
    results = doctest.testmod(module, optionflags=doctest.ELLIPSIS)  # type: ignore[arg-type]
    assert results.attempted > 0
    assert results.failed == 0
