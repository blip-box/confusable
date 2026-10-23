import importlib.metadata
import subprocess
import sys

import confusable

# Prints the modules that importing the package adds, in a fresh interpreter.
_NEW_MODULES = (
    "import sys; before = set(sys.modules); import confusable; "
    "print(*sorted(set(sys.modules) - before))"
)


def test_version_matches_distribution_metadata() -> None:
    assert confusable.__version__ == importlib.metadata.version("confusable")


def test_has_no_runtime_dependencies() -> None:
    requirements = importlib.metadata.requires("confusable") or []
    assert [r for r in requirements if "extra ==" not in r] == []


def test_import_loads_no_tables_or_heavy_modules() -> None:
    """Importing the package stays fast: the tables load on first use.

    Without cached bytecode the generated tables take about 100 ms to import.
    A dataclass would import inspect and ast, and a NamedTuple annotationlib
    on Python 3.14. Checking which modules load, rather than timing the
    import, keeps the test from being flaky.
    """
    result = subprocess.run(
        [sys.executable, "-c", _NEW_MODULES],
        capture_output=True,
        text=True,
        check=True,
    )
    imported = set(result.stdout.split())
    assert "confusable._skeleton" in imported
    assert sorted(m for m in imported if m.startswith("confusable._data.")) == []
    heavy = {"annotationlib", "ast", "dataclasses", "importlib.metadata", "inspect"}
    assert sorted(imported & heavy) == []


def test_unicode_version_is_the_pinned_one() -> None:
    from tools.unicode_sources import UNICODE_VERSION

    assert confusable.unicode_version == UNICODE_VERSION
