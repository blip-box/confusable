"""The API of confusable_homoglyphs 3.3.1, on confusable's Unicode data.

Existing code switches by changing one import::

    from confusable_homoglyphs import categories, confusables  # before
    from confusable.compat.homoglyphs import categories, confusables  # after

The functions and their return values are those of confusable_homoglyphs
3.3.1, with its data rebuilt from the Unicode files that confusable pins (see
``confusable.unicode_version``). The data differs from what that package's own
generator makes in two ways, both fixes:

- Right-to-left characters, such as Arabic and Hebrew letters, are found. Its
  generator reads the characters from the comments in confusables.txt, which
  wrap them in invisible LEFT-TO-RIGHT MARKs, so it stores Arabic letters
  under keys that a letter never matches, and is_confusable misses them.
- Four entries its generator cannot parse are kept: U+2028 LINE SEPARATOR,
  U+2029 PARAGRAPH SEPARATOR, U+3164 HANGUL FILLER and U+FFA0 HALFWIDTH
  HANGUL FILLER, the blank characters of "invisible" user names.

Results hold fresh lists, so changing one does not change the data.

Code that cannot change its import can give confusable_homoglyphs itself this
data. ``export(directory)``, or on the command line::

    python -m confusable.compat.homoglyphs export /srv/app/confusable-data

writes ``categories.json`` and ``confusables.json`` there, laid out as that
package writes and reads them, and the unchanged package loads them instead
of its own when the CONFUSABLE_DATA environment variable names the
directory::

    export CONFUSABLE_DATA=/srv/app/confusable-data

It reads the variable when it is first imported, so set it before the
interpreter starts. The package's own command line, ``confusable_homoglyphs
check`` and ``update``, is not provided. For new code, prefer confusable's own
API: ``confusable.match`` and ``confusable.restriction_level`` follow UTS #39,
which these heuristics do not.
"""

from __future__ import annotations

import os

from confusable.compat.homoglyphs import categories, confusables

__all__ = ["categories", "confusables", "export"]


def export(directory: str | os.PathLike[str]) -> list[str]:
    """Write confusable_homoglyphs' two data files, with this data, to directory.

    ``categories.json`` and ``confusables.json`` are laid out as
    confusable_homoglyphs 3.3.1 writes and reads them, so that the unchanged
    package loads them from the directory its CONFUSABLE_DATA environment
    variable names (see the package docstring). The directory is created if
    it does not exist and the two files are overwritten. Returns their paths.
    """
    import json

    os.makedirs(directory, exist_ok=True)
    files = (
        ("categories.json", categories.categories_data),
        ("confusables.json", confusables.confusables_data),
    )
    paths = []
    for name, data in files:
        path = os.path.join(directory, name)
        # json.dump's defaults, as the package's own generator writes the
        # files: ASCII only, so that the package, which opens them without
        # naming an encoding, reads them back on any platform.
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file)
        paths.append(path)
    return paths
