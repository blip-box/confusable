"""The General Security Profile for identifiers (UTS #39 section 3.1)."""

from __future__ import annotations

from confusable._data import identifiers as _data
from confusable._lookup import Ranges

# Identifier_Status=Allowed.
ALLOWED = Ranges(_data.IDENTIFIER_ALLOWED_RANGES)


def in_profile(text: str) -> bool:
    """Return whether every character of text has Identifier_Status=Allowed."""
    return all(ord(c) in ALLOWED for c in text)
