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

Results hold fresh lists, so changing one does not change the data. The
package's command line and its CONFUSABLE_DATA environment variable are not
provided. For new code, prefer confusable's own API: ``confusable.match`` and
``confusable.restriction_level`` follow UTS #39, which these heuristics do not.
"""

from confusable.compat.homoglyphs import categories, confusables

__all__ = ["categories", "confusables"]
