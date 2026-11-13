"""Runs the docstring examples of every module in the package.

Each module is one case, so a wrong example names its module. A second test
checks that every source file holding an example yields a doctest, so that an
example cannot drop out of the run unnoticed.
"""

import doctest
import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

import pytest

import confusable

MODULE_NAMES = sorted(
    info.name for info in pkgutil.walk_packages(confusable.__path__, "confusable.")
)


def _doctests(module: ModuleType) -> list[doctest.DocTest]:
    found = doctest.DocTestFinder().find(module, module.__name__)
    return [test for test in found if test.examples]


@pytest.mark.parametrize("name", MODULE_NAMES, ids=MODULE_NAMES)
def test_docstring_examples(name: str) -> None:
    module = importlib.import_module(name)
    for test in _doctests(module):
        report: list[str] = []
        runner = doctest.DocTestRunner(verbose=False)
        runner.run(test, out=report.append)
        assert runner.failures == 0, "".join(report)


def test_every_module_with_examples_yields_doctests() -> None:
    with_examples = []
    for name in MODULE_NAMES:
        module = importlib.import_module(name)
        assert module.__file__ is not None
        if ">>> " in Path(module.__file__).read_text(encoding="utf-8"):
            with_examples.append(name)
            assert _doctests(module), f"{name} has '>>> ' but no doctest runs"
    assert with_examples
