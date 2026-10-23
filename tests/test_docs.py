import doctest

import pytest

from confusable import (
    _identifiers,
    _invisible,
    _marks,
    _numbers,
    _restriction,
    _skeleton,
)


@pytest.mark.parametrize(
    "module", [_identifiers, _invisible, _marks, _numbers, _restriction, _skeleton]
)
def test_docstring_examples(module: object) -> None:
    results = doctest.testmod(module, optionflags=doctest.ELLIPSIS)  # type: ignore[arg-type]
    assert results.attempted > 0
    assert results.failed == 0
