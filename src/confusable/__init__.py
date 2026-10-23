"""Unicode spoofing and confusable detection (UTS #39) in pure Python."""

from confusable import _data
from confusable._identifiers import (
    IdentifierStatus,
    IdentifierType,
    identifier_status,
    identifier_types,
    is_allowed,
    isxidcontinue,
    isxidstart,
)
from confusable._invisible import Invisible, find_invisible, has_invisible
from confusable._marks import has_hidden_overlay, has_unlikely_marks
from confusable._numbers import has_mixed_numbers
from confusable._restriction import RestrictionLevel, is_mixed_script, restriction_level
from confusable._skeleton import Match, match, skeleton

# Kept in step with pyproject.toml by tests/test_package.py. A literal, because
# importlib.metadata alone would add about 100 ms to importing the package.
__version__ = "0.1.0.dev0"

# The Unicode version of every table and algorithm in the package.
unicode_version = _data.UNICODE_VERSION

__all__ = [
    "IdentifierStatus",
    "IdentifierType",
    "Invisible",
    "Match",
    "RestrictionLevel",
    "__version__",
    "find_invisible",
    "has_hidden_overlay",
    "has_invisible",
    "has_mixed_numbers",
    "has_unlikely_marks",
    "identifier_status",
    "identifier_types",
    "is_allowed",
    "is_mixed_script",
    "isxidcontinue",
    "isxidstart",
    "match",
    "restriction_level",
    "skeleton",
    "unicode_version",
]
