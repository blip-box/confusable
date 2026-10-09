"""Unicode spoofing and confusable detection (UTS #39) in pure Python."""

from importlib.metadata import version as _version

__version__ = _version("confusable")

__all__ = ["__version__"]
