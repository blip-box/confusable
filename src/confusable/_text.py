"""The argument check every public function makes on the text it is given.

The functions take str and nothing else, as unicodedata's do. Without the
check, an ASCII fast path such as `text.isascii()` would accept bytes, which
have the same method, and answer for them; other inputs would fail somewhere
inside with an error that names a helper.
"""

from __future__ import annotations


def require_str(value: object, function: str, position: int = 1) -> None:
    """Raise TypeError unless value is a str, naming the public function.

    >>> require_str(b"abc", "skeleton")
    Traceback (most recent call last):
    TypeError: skeleton() argument 1 must be str, not bytes
    """
    if not isinstance(value, str):
        raise TypeError(
            f"{function}() argument {position} must be str, not {type(value).__name__}"
        )
