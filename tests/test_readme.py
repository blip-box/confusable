"""README.md states results that the library has to keep giving.

README.md is the package's page on PyPI. Its Python blocks show calls with the
result written in a comment, such as `confusable.match("rn", "m")  #
Match.SINGLE_SCRIPT`. This module runs those blocks and checks every result
against the value written here from that comment, so the page cannot drift
from what the library does (C-CORRECT-1). A block that disappears, a new
expression without an expected value, or a changed result fails the test.
"""

import ast
import functools
import re
from pathlib import Path

import pytest

from confusable import IdentifierType, Invisible, Match, RestrictionLevel

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
# A block opens with a line that is exactly ```python and closes with ```.
FENCE = re.compile(r"^```python\n(.*?)^```$", re.MULTILINE | re.DOTALL)

# The README uses these names without defining them, in blocks 2 and 6.
NAME = "Ren\u00e9e"
BIO = "Caf\u00e9 owner in M\u00fcnchen."

# One list per Python block of README.md, in order, with one entry per
# top-level expression statement, in order. Each comment quotes the README
# line the entry checks; the value comes from that line's own comment.
EXPECTED: list[list[object]] = [
    [
        "paypal",  # confusable.skeleton("p\u0430ypal")
        Match.MIXED_SCRIPT,  # confusable.match("paypal", "p\u0430ypal")
        Match.SINGLE_SCRIPT,  # confusable.match("rn", "m")
        None,  # confusable.match("paypal", "paypa1x")
        "invoiceexe.jpg",  # confusable.skeleton("invoice\u202egpj.exe")
    ],
    [
        RestrictionLevel.SINGLE_SCRIPT,  # confusable.restriction_level("caf\u00e9")
        RestrictionLevel.HIGHLY_RESTRICTIVE,  # restriction_level("abc\u3042")
        RestrictionLevel.MINIMALLY_RESTRICTIVE,  # restriction_level("p\u0430ypal")
        True,  # confusable.is_mixed_script("p\u0430ypal")
        # restriction_level(name) <= RestrictionLevel.HIGHLY_RESTRICTIVE, which
        # the README states for its kind of name; NAME is Latin only.
        True,
    ],
    [
        True,  # confusable.is_allowed("paypal")
        False,  # confusable.is_allowed("pay pal")
        True,  # confusable.is_allowed("\u0114")
        # identifier_types("\u200d"), a frozenset written as a set
        frozenset({IdentifierType.DEFAULT_IGNORABLE}),
        (False, True),  # isxidstart("_"), isxidcontinue("_")
        True,  # is_allowed("\u0dc1\u0dca\u200d\u0dbb\u0dd3", joining_controls=True)
        False,  # is_allowed("pay\u200dpal", joining_controls=True)
    ],
    [
        True,  # confusable.has_mixed_numbers("1\u0661")
        True,  # confusable.has_unlikely_marks("e\u0301\u0301")
        True,  # confusable.has_hidden_overlay("i\u0307")
    ],
    [
        [(3, Invisible.DEFAULT_IGNORABLE)],  # find_invisible("pay\u200bpal")
        [(7, Invisible.BIDI_CONTROL)],  # find_invisible("invoice\u202egpj.exe")
        # find_invisible("hi\U000e0068\U000e0069"): two Invisible.TAG
        [(2, Invisible.TAG), (3, Invisible.TAG)],
        False,  # has_invisible("\U0001f468\u200d\U0001f469\u200d\U0001f467")
    ],
    [
        # [str(g) for g in iter_graphemes("e\u0301\U0001f1fa\U0001f1f8")]
        ["e\u0301", "\U0001f1fa\U0001f1f8"],
        NAME,  # confusable.truncate(name, 32): NAME is under 32 graphemes
        BIO,  # confusable.truncate(bio, 300, max_utf8_bytes=3000): so is BIO
    ],
    [
        True,  # confusables.is_dangerous("p\u0430ypal")
    ],
]


def _blocks() -> list[str]:
    return FENCE.findall(README)


@functools.cache
def _results() -> list[list[object]]:
    """Run every block in order in one namespace; return each block's values."""
    namespace: dict[str, object] = {"name": NAME, "bio": BIO}
    results: list[list[object]] = []
    for source in _blocks():
        values: list[object] = []
        for stmt in ast.parse(source, "README.md").body:
            if isinstance(stmt, ast.Import | ast.ImportFrom):
                module = ast.Module(body=[stmt], type_ignores=[])
                exec(compile(module, "README.md", "exec"), namespace)
            elif isinstance(stmt, ast.Expr):
                code = compile(ast.Expression(stmt.value), "README.md", "eval")
                values.append(eval(code, namespace))
            else:
                pytest.fail(f"README.md line {stmt.lineno}: unexpected statement")
        results.append(values)
    return results


def _check(actual: object, expected: object) -> None:
    # None, True and False by identity, so a falsy object cannot pass for None
    # (C-API-1); everything else by type and value, so an int cannot pass for
    # an enum member, nor a tuple for a list.
    if expected is None or isinstance(expected, bool):
        assert actual is expected
        return
    assert type(actual) is type(expected)
    if isinstance(expected, list | tuple):
        assert isinstance(actual, list | tuple)
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected, strict=True):
            _check(a, e)
    elif isinstance(expected, frozenset):
        assert isinstance(actual, frozenset)
        assert {type(a) for a in actual} == {type(e) for e in expected}
        assert actual == expected
    else:
        assert actual == expected


def test_block_count() -> None:
    assert len(_blocks()) == len(EXPECTED)


@pytest.mark.parametrize("index", range(len(EXPECTED)))
def test_block_results(index: int) -> None:
    results = _results()
    assert len(results) == len(EXPECTED)
    assert len(results[index]) == len(EXPECTED[index])
    for actual, expected in zip(results[index], EXPECTED[index], strict=True):
        _check(actual, expected)


def test_check_is_strict() -> None:
    with pytest.raises(AssertionError):
        _check([], None)
    with pytest.raises(AssertionError):
        _check(0, False)
    with pytest.raises(AssertionError):
        _check(int(RestrictionLevel.SINGLE_SCRIPT), RestrictionLevel.SINGLE_SCRIPT)
    with pytest.raises(AssertionError):
        _check(((3, Invisible.DEFAULT_IGNORABLE),), [(3, Invisible.DEFAULT_IGNORABLE)])
