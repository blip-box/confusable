# Accepting names safely

`confusable` gives you the checks. Which ones apply depends on what the text is
for. UTS #39 defines each check but leaves the policy to you, so this page
gives three recipes, for usernames, display names and filenames, and shows how
to refuse a name that looks like one you already have. Adapt them: they are
starting points, not the only reasonable policy. The code on this page runs in
the test suite (`tests/test_recipes.py`).

| Text | Held to | Checks |
|---|---|---|
| Usernames, handles, slugs, project names | The identifier profile | `is_allowed`, `restriction_level`, `has_mixed_numbers`, `has_unlikely_marks`, `has_hidden_overlay`, and a skeleton that must be unique |
| Display names | No character profile: spaces, punctuation, emoji and mixed scripts are fine | `has_invisible`, `has_unlikely_marks`, `truncate`, and a skeleton compared with the names you protect |
| Filenames | The file system's own rules | `has_invisible`, and the extension a reader sees |

None of the checks needs the text normalized first: each gives the same answer
for NFC and NFD text.

## Usernames, handles and slugs

```python
import confusable
from confusable import RestrictionLevel


def username_problem(name: str) -> str | None:
    """Return why name cannot be a username, or None when it can."""
    if not confusable.is_allowed(name):
        return "a character outside the identifier profile"
    if confusable.restriction_level(name) > RestrictionLevel.HIGHLY_RESTRICTIVE:
        return "scripts that are not used together"
    if confusable.has_mixed_numbers(name):
        return "digits from different number systems"
    if confusable.has_unlikely_marks(name) or confusable.has_hidden_overlay(name):
        return "combining marks that pile up or hide"
    return None
```

- `is_allowed` is UTS #39's General Security Profile. Letters, digits and the
  few punctuation characters identifiers use, such as `_`, `-` and `.`, are in.
  Spaces, symbols, emoji and invisible characters are out.
- UTS #39 defines the restriction levels but recommends none.
  `HIGHLY_RESTRICTIVE` is the default of ICU's SpoofChecker. It allows a single
  script, or Latin with Han and Japanese kana, with Han and Bopomofo, or with
  Han and Hangul. Latin with Cyrillic or Greek is refused.
- The mark checks refuse "Zalgo" text and an `i` given a second dot above,
  which its own dot hides.

```python
username_problem("john_smith42")  # None
username_problem("pay pal")  # 'a character outside the identifier profile'
username_problem("p\u0430ypal")  # 'scripts that are not used together': Cyrillic a
username_problem("i\u0307")  # 'combining marks that pile up or hide'
username_problem("\u0430\u0441\u0435")  # None: all Cyrillic, caught next
```

## Refusing a name that looks like another

Two strings are confusable when their skeletons are equal. A unique index on
the skeleton therefore refuses look-alikes the way a unique index on the name
refuses duplicates.

```python
def username_keys(name: str) -> tuple[str, str]:
    """Return the keys that must each be unique among usernames."""
    return confusable.skeleton(name), confusable.skeleton(name.casefold())
```

- The first key is the name as a reader sees it. `skeleton` keeps case,
  because a reader can tell `Paypal` from `paypal`. It maps capital `I` and
  small `l` to the same prototype, because a reader often cannot.
- The second key is for names that are compared without regard to case, as
  most usernames are: `PAYPA1` and `paypal` share it. UTS #39's skeleton has no
  case-folding step, so this key is this page's choice. Drop it where names
  are case-sensitive.
- `str.casefold` follows the interpreter's Unicode version, not the pinned
  one, so an interpreter older than Unicode 18 does not fold the cased letters
  added since its own version.
- Store `confusable.unicode_version` with the keys. Skeletons change with the
  Unicode data, and UTS #39 says that stored skeletons must be recomputed when
  the version changes.

The same keys protect names you reserve:

```python
RESERVED = {key for name in ("admin", "root", "support") for key in username_keys(name)}


def is_reserved(name: str) -> bool:
    return any(key in RESERVED for key in username_keys(name))
```

```python
username_keys("\u0430\u0441\u0435") == username_keys("ace")  # True: all Cyrillic
username_keys("PAYPA1")[1] == username_keys("paypal")[1]  # True
username_keys("Paypal")[0] == username_keys("paypal")[0]  # False: case shows
is_reserved("\u0430dmin")  # True: Cyrillic a
is_reserved("ADMIN")  # True
is_reserved("administrator")  # False
```

## Display names

```python
def display_name_problem(name: str) -> str | None:
    """Return why name cannot be a display name, or None when it can."""
    if confusable.has_invisible(name):
        return "an invisible or control character"
    if confusable.has_unlikely_marks(name):
        return "combining marks that pile up"
    if confusable.truncate(name, 50, max_utf8_bytes=200) != name:
        return "too long"
    return None


STAFF = {key for name in ("Support Team", "Ada Admin") for key in username_keys(name)}


def impersonates_staff(name: str) -> bool:
    return any(key in STAFF for key in username_keys(name))
```

- Display names are not held to the identifier profile: people write their
  names with spaces, punctuation, emoji and more than one script.
- `has_invisible` refuses zero-width characters, bidirectional controls and
  Tag characters, and accepts them where they have a visible job: emoji ZWJ
  sequences, flags and variation sequences.
- A grapheme limit is what a reader counts, but a grapheme can be any size, so
  the byte limit bounds what you store.
- The skeleton keys compare a name with the names you protect, here the staff
  account's.

```python
display_name_problem("Ana Lima \U0001f1e7\U0001f1f7")  # None: a flag
display_name_problem("Ana\u200bLima")  # 'an invisible or control character'
display_name_problem("Z\u0301\u0301\u0301")  # 'combining marks that pile up'
impersonates_staff("Support Tearn")  # True: rn for m
impersonates_staff("SUPPORT TEAM")  # True
```

## Filenames

```python
def filename_problem(name: str) -> str | None:
    """Return why name cannot be an uploaded file's name, or None when it can."""
    if confusable.has_invisible(name):
        return "an invisible or control character"
    _, dot, extension = name.rpartition(".")
    shown = confusable.skeleton(name)
    if dot and not shown.endswith(confusable.skeleton(dot + extension)):
        return "a reader would see a different extension"
    return None
```

- `has_invisible` refuses the RIGHT-TO-LEFT OVERRIDE in
  `"invoice\u202egpj.exe"`, which a reader sees as `invoiceexe.jpg`.
- The skeleton is in display order, so the second check also catches
  reordering that right-to-left letters cause without any control character.
  A name whose extension and the part before it are both right-to-left is
  refused: it shows with the extension first, and a reader cannot tell which
  part it is.
- Length limits and the names a file system reserves are the file system's
  rules, not Unicode's, and this library does not check them.

```python
filename_problem("report.pdf")  # None
filename_problem("\u05d0\u05d1.pdf")  # None: a Hebrew name
filename_problem("invoice\u202egpj.exe")  # 'an invisible or control character'
filename_problem("\u05d0.\u05d1")  # 'a reader would see a different extension'
```
