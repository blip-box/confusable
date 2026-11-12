"""docs/accepting-names.md runs: its recipes give the results the page states.

The page's Python blocks define the recipes and then call them, with the
result written in a comment. This module runs the blocks in order in one
namespace and checks every call's result against the value written here from
that comment, so the page cannot drift from what the library does
(C-CORRECT-1). A block that disappears, a new call without an expected value,
or a changed result fails the test.
"""

import ast
import functools
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "accepting-names.md").read_text(encoding="utf-8")
FENCE = re.compile(r"^```python\n(.*?)^```$", re.MULTILINE | re.DOTALL)
DEFINITIONS = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign)

# One list per Python block of the page, in order, with one entry per
# top-level expression statement. Blocks that only define things have none.
EXPECTED: list[list[object]] = [
    [],  # username_problem
    [
        None,  # username_problem("john_smith42")
        "a character outside the identifier profile",  # ("pay pal")
        "scripts that are not used together",  # ("p\u0430ypal")
        "combining marks that pile up or hide",  # ("i\u0307")
        None,  # ("\u0430\u0441\u0435"), all Cyrillic
    ],
    [],  # username_keys
    [],  # RESERVED, is_reserved
    [
        True,  # username_keys("\u0430\u0441\u0435") == username_keys("ace")
        True,  # username_keys("PAYPA1")[1] == username_keys("paypal")[1]
        False,  # username_keys("Paypal")[0] == username_keys("paypal")[0]
        True,  # is_reserved("\u0430dmin")
        True,  # is_reserved("ADMIN")
        False,  # is_reserved("administrator")
    ],
    [],  # display_name_problem, STAFF, impersonates_staff
    [
        None,  # display_name_problem("Ana Lima " + a flag)
        "an invisible or control character",  # ("Ana\u200bLima")
        "combining marks that pile up",  # ("Z\u0301\u0301\u0301")
        True,  # impersonates_staff("Support Tearn")
        True,  # impersonates_staff("SUPPORT TEAM")
    ],
    [],  # filename_problem
    [
        None,  # filename_problem("report.pdf")
        None,  # filename_problem("\u05d0\u05d1.pdf")
        "an invisible or control character",  # ("invoice\u202egpj.exe")
        "a reader would see a different extension",  # ("\u05d0.\u05d1")
    ],
]


def _blocks() -> list[str]:
    return FENCE.findall(PAGE)


@functools.cache
def _results() -> list[list[object]]:
    """Run every block in order in one namespace; return each block's values."""
    namespace: dict[str, object] = {}
    results: list[list[object]] = []
    for source in _blocks():
        values: list[object] = []
        for stmt in ast.parse(source, "accepting-names.md").body:
            if isinstance(stmt, DEFINITIONS):
                module = ast.Module(body=[stmt], type_ignores=[])
                exec(compile(module, "accepting-names.md", "exec"), namespace)
            elif isinstance(stmt, ast.Expr):
                code = compile(ast.Expression(stmt.value), "accepting-names.md", "eval")
                values.append(eval(code, namespace))
            else:
                pytest.fail(
                    f"accepting-names.md line {stmt.lineno}: unexpected statement"
                )
        results.append(values)
    return results


def test_block_count() -> None:
    assert len(_blocks()) == len(EXPECTED)


@pytest.mark.parametrize("index", range(len(EXPECTED)))
def test_block_results(index: int) -> None:
    results = _results()
    assert len(results[index]) == len(EXPECTED[index])
    for actual, expected in zip(results[index], EXPECTED[index], strict=True):
        # None, True and False by identity (C-API-1); strings by type and value.
        if expected is None or isinstance(expected, bool):
            assert actual is expected
        else:
            assert type(actual) is type(expected)
            assert actual == expected
