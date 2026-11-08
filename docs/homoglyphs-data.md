# The data bug in confusable_homoglyphs, and three ways around it

[`confusable_homoglyphs`](https://pypi.org/project/confusable-homoglyphs/) is a
Python package that finds characters which look like characters of another
script. Its latest release, 3.3.1, is used by django-registration, Weblate,
opensquat and many smaller projects. `confusable.compat.homoglyphs` reproduces
its API on current Unicode data, and while building it we found a bug in the
way the package generates its data: it misses every right-to-left character,
Arabic and Hebrew letters among them. This page says what the bug is, how far
it reaches, and gives three ways to get correct data, from changing one import
to changing nothing in your code.

The package has done its job well for years, and the bug is a parsing detail
in its data generator, not a flaw in its design. We have told its maintainer
(see the end of this page).

## What the bug is

Both packages build their data from Unicode's
[`confusables.txt`](https://www.unicode.org/Public/18.0.0/security/confusables.txt),
whose lines look like this (`<LRM>` stands for an invisible U+200E LEFT-TO-RIGHT
MARK):

```text
0627 ;	006C ;	MA	# ( <LRM>ا<LRM> → l ) ARABIC LETTER ALEF → LATIN SMALL LETTER L	#
```

The first two fields are the code points of the look-alike pair. The comment
repeats the two characters for human readers, and because the file is read
left to right, it wraps every right-to-left character in a LEFT-TO-RIGHT MARK
on each side, so that the comment displays in order.

The package's generator, `generate_confusables()` in `confusable_homoglyphs/cli.py`,
reads the characters from the comment with a regular expression, not from the
code point fields. So it stores the Arabic letter with its two marks: the key
in `confusables.json` is `"\u200e\u0627\u200e"`, a string of three characters.
`is_confusable()` looks up each character of its input one at a time, and the
one-character string `"\u0627"` matches nothing. The same happens to every
right-to-left character in the file, Arabic above all, then Hebrew, Syriac,
N'Ko and a few other scripts: 1,371 of the 9,619 keys in the shipped
`confusables.json` are wrapped in marks that no input character ever carries.

The regular expression also expects the comment to show a visible character,
so it skips the four lines whose characters show as blanks: U+2028 LINE
SEPARATOR, U+2029 PARAGRAPH SEPARATOR, U+3164 HANGUL FILLER and U+FFA0
HALFWIDTH HANGUL FILLER, the characters of "blank" user names, and with them
their partner U+1160 HANGUL JUNGSEONG FILLER.

## Reproducer

With `confusable-homoglyphs==3.3.1` installed:

```python
from confusable_homoglyphs import confusables

# ARABIC LETTER ALEF and HEBREW LETTER VAV both look like l. Not found:
confusables.is_confusable("pa\u0627ypal", preferred_aliases=["latin"])  # False
confusables.is_confusable("pa\u05d5pal", preferred_aliases=["latin"])  # False
# CYRILLIC SMALL LETTER A, a left-to-right character, is found:
confusables.is_confusable("p\u0430ypal", preferred_aliases=["latin"])  # [{...}]

"\u0627" in confusables.confusables_data  # False
"\u200e\u0627\u200e" in confusables.confusables_data  # True
```

With `confusable.compat.homoglyphs` in place of `confusable_homoglyphs`, the
first two calls find the letters.

## How far it reaches

Measured on 2026-11-08 with `confusable-homoglyphs==3.3.1` and `confusable`
0.1.0a2 side by side, on Python 3.12, over the 4,120 strings of confusable's
conformance corpus (`tests/conformance/fixtures/homoglyphs.txt.gz`).

| | `confusable_homoglyphs` 3.3.1 | `confusable.compat.homoglyphs` |
|---|---|---|
| Keys in `confusables_data` | 9,619 | 9,849 |
| Keys wrapped in LEFT-TO-RIGHT MARKs | 1,371 | 0 |
| Single-character keys in the Arabic script | 44 | 1,063 |
| Single-character keys in the Hebrew script | 19 | 54 |
| Unicode version of the data | 15.1 | 18.0 |

Part of the difference in the totals is Unicode 15.1 to 18.0 growth, not the
bug.

**What is affected.** `is_confusable()` with `preferred_aliases`, the question
"does any character of this string imitate my script": for Arabic and Hebrew
look-alikes it answers no. `is_dangerous()` with `preferred_aliases` inherits
that. `is_dangerous()` with its default arguments is affected only for strings
that contain no ASCII letter; see below.

**What is not affected.** `is_dangerous(value)` with its default arguments,
which is how django-registration (`validate_confusables`,
`validate_confusables_email`), Weblate (`weblate/utils/validators.py`) and
opensquat (`opensquat/homograph.py`) call it. A string is dangerous when it
mixes scripts and any of its characters has a look-alike in the data. Every
ASCII letter has one, so for a string with an ASCII letter in it the Arabic
and Hebrew entries never decide the answer: `is_dangerous("pa\u0627ypal")` is
True with either data set, because of the Latin letters. Comparing the
package's own generator and the corrected data on the same Unicode 18 files,
`is_dangerous()` changes for 129 of the 4,120 corpus strings, all from False
to True, and none of the 129 contains an ASCII letter: they mix a
right-to-left script with another non-Latin script, or with accented Latin
letters that have no look-alike of their own. `is_mixed_script()` and the `categories` module are
not affected at all: the generator reads `Scripts.txt` correctly.

Moving to the corrected data also moves from Unicode 15.1 to Unicode 18.0,
which changes some answers in both directions, as any data update does: over
the corpus, `is_dangerous()` with default arguments changes for 330 strings
between the shipped 15.1 data and the generator's own output on the 18.0
files, 268 of them to True and 62 to False, because of look-alike pairs that
Unicode added or removed since 15.1, and of code points that were unassigned
then and have a script now.

## Three ways to correct data

All three come with `confusable` (`pip install confusable`), which has no
dependencies of its own.

### 1. Change the import

Where you own the code that imports the package, change one line:

```python
from confusable.compat.homoglyphs import categories, confusables
```

The functions, their arguments and their results are those of
`confusable_homoglyphs` 3.3.1, on confusable's data. For new code, prefer
confusable's own `match()` and `restriction_level()`, which follow Unicode
Technical Standard #39; the compat module keeps the package's heuristics as
they are.

### 2. Export the data files and point `CONFUSABLE_DATA` at them

`confusable_homoglyphs` loads its two data files from the directory named by
the `CONFUSABLE_DATA` environment variable when it is set, and from its own
directory otherwise. So the unchanged package can read corrected files:

```bash
python -m confusable.compat.homoglyphs export /srv/app/confusable-data
```

writes `categories.json` and `confusables.json` there in the package's own
layout. Then set the variable before the interpreter starts, in the service
unit, the container image or the shell that launches the application:

```bash
export CONFUSABLE_DATA=/srv/app/confusable-data
```

No code changes anywhere. The package reads the variable when it is first
imported, so setting it later in the process has no effect. Export again when
you upgrade `confusable`, so that the files follow its Unicode version. The
same export is available from Python as
`confusable.compat.homoglyphs.export(directory)`.

### 3. Alias the package with `install()`

Where you control the entry point but not the libraries that import
`confusable_homoglyphs`, and an environment variable is not an option:

```python
import confusable.compat.homoglyphs

confusable.compat.homoglyphs.install()
```

registers `confusable.compat.homoglyphs` in `sys.modules` under the names
`confusable_homoglyphs`, `confusable_homoglyphs.categories` and
`confusable_homoglyphs.confusables`. Every later import of the package, in
any library, gets confusable's modules and data. Call it before anything
imports the package, for example at the top of a Django settings module: it
raises `RuntimeError` if `confusable_homoglyphs` is already imported, because
the code that imported it would keep the old modules, and it does nothing
when called a second time. It is opt-in because it changes what other
libraries get from their own import. Only `categories` and `confusables` are
provided, not the package's `utils` or `cli` modules.

### Which one

| You can change | Use |
|---|---|
| The code that imports the package | the import (1) |
| Only the environment the application runs in | `CONFUSABLE_DATA` (2) |
| Only the entry point of the application | `install()` (3) |

## Upstream

We have reported the bug to the maintainer of `confusable_homoglyphs`, with an
offer of a patch to the generator: read the two characters from the code
point fields of each line, as `confusable.compat.homoglyphs` and its test
oracle do, and take only the names from the comment. Until a release with
corrected data is out, the three ways above work with the current one.
