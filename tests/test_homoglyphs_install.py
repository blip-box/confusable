"""install() makes import confusable_homoglyphs import confusable.compat.homoglyphs.

Every test runs in a fresh interpreter: install() changes sys.modules for the
rest of the process.
"""

import json
import subprocess
import sys

from tests import homoglyphs_package

INSTALLED = """
import importlib
import json

import confusable.compat.homoglyphs as ours

ours.install()

import confusable_homoglyphs
import confusable_homoglyphs.confusables
from confusable_homoglyphs import categories, confusables


def latin(string):
    return bool(confusables.is_confusable(string, preferred_aliases=["latin"]))


print(json.dumps({
    "package": confusable_homoglyphs is ours,
    "categories": categories is ours.categories,
    "confusables": confusables is ours.confusables,
    "imported": (
        importlib.import_module("confusable_homoglyphs.confusables")
        is ours.confusables
    ),
    # The two cases the package's own data misses, and one it finds.
    "arabic": latin("pa" + chr(0x627) + "ypal"),
    "hebrew": latin("pa" + chr(0x5D5) + "pal"),
    "cyrillic": confusables.is_dangerous("p" + chr(0x430) + "ypal"),
    "alias": categories.alias("A"),
}))
"""

AGAIN = """
import sys

import confusable.compat.homoglyphs as ours

ours.install()
before = {name: module for name, module in sys.modules.items() if "homoglyphs" in name}
ours.install()
after = {name: module for name, module in sys.modules.items() if "homoglyphs" in name}
print(before == after and "confusable_homoglyphs.categories" in before)
"""

# A stand-in for the real package, for when it is not installed.
STAND_IN = """
import sys
import types

stand_in = types.ModuleType("confusable_homoglyphs")
sys.modules["confusable_homoglyphs"] = stand_in

import confusable.compat.homoglyphs as ours

try:
    ours.install()
except RuntimeError as error:
    print("RuntimeError:", error)
print(sys.modules["confusable_homoglyphs"] is stand_in)
print(sorted(name for name in sys.modules if name.startswith("confusable_homoglyphs")))
"""

REAL_PACKAGE = """
from confusable_homoglyphs import confusables

import confusable.compat.homoglyphs as ours

try:
    ours.install()
except RuntimeError as error:
    print("RuntimeError:", error)
print(confusables.__file__)
"""

REFUSED = "RuntimeError: confusable_homoglyphs is already imported"


def run(
    code: str, python: str = sys.executable, env: dict[str, str] | None = None
) -> str:
    result = subprocess.run(
        [python, "-c", code], capture_output=True, text=True, check=False, env=env
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_install_aliases_the_package_and_its_modules() -> None:
    output = json.loads(run(INSTALLED))
    assert output == {
        "package": True,
        "categories": True,
        "confusables": True,
        "imported": True,
        "arabic": True,
        "hebrew": True,
        "cyrillic": True,
        "alias": "LATIN",
    }


def test_a_second_install_is_a_no_op() -> None:
    assert run(AGAIN).split() == ["True"]


def test_install_refuses_when_the_package_is_already_imported() -> None:
    lines = run(STAND_IN).splitlines()
    assert lines[0].startswith(REFUSED)
    assert "before anything imports it" in lines[0]
    # And leaves sys.modules as it was.
    assert lines[1] == "True"
    assert lines[2] == "['confusable_homoglyphs']"


def test_install_refuses_after_the_real_package_is_imported() -> None:
    """The same, with confusable_homoglyphs 3.3.1 itself; skips without it."""
    python, env = homoglyphs_package.interpreter()
    lines = run(REAL_PACKAGE, python, env).splitlines()
    assert lines[0].startswith(REFUSED)
    assert "confusable_homoglyphs" in lines[1]
