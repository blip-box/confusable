"""Unicode spoofing and confusable detection (UTS #39) in pure Python."""

from confusable import _data
from confusable._restriction import RestrictionLevel, is_mixed_script, restriction_level
from confusable._skeleton import Match, match, skeleton

# Kept in step with pyproject.toml by tests/test_package.py. A literal, because
# importlib.metadata alone would add about 100 ms to importing the package.
__version__ = "0.1.0.dev0"

# The Unicode version of every table and algorithm in the package.
unicode_version = _data.UNICODE_VERSION

__all__ = [
    "Match",
    "RestrictionLevel",
    "__version__",
    "is_mixed_script",
    "match",
    "restriction_level",
    "skeleton",
    "unicode_version",
]
