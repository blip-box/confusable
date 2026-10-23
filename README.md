# confusable

Unicode spoofing and confusable detection for Python, following
[Unicode Technical Standard #39](https://www.unicode.org/reports/tr39/). Pure Python,
no runtime dependencies.

> **Status: pre-alpha.** Look-alike detection (`skeleton`, `match`), mixed-script
> detection and restriction levels work and pass their conformance tests; the other
> features below are planned. Nothing is on PyPI yet.

## Usage

```python
import confusable

confusable.skeleton("p\u0430ypal")  # 'paypal' (with CYRILLIC SMALL LETTER A)
confusable.match("paypal", "p\u0430ypal")  # Match.MIXED_SCRIPT, which is true
confusable.match("rn", "m")  # Match.SINGLE_SCRIPT
confusable.match("paypal", "paypa1x")  # Match(0), which is false

# The skeleton follows display order, so a right-to-left override is seen
# the way a reader sees it:
confusable.skeleton("invoice\u202egpj.exe")  # 'invoiceexe.jpg'
```

Restriction levels (UTS #39 section 5.2) rank how safely a string mixes scripts,
from `ASCII_ONLY` to `UNRESTRICTED`, using the General Security Profile:

```python
confusable.restriction_level("caf\u00e9")  # RestrictionLevel.SINGLE_SCRIPT
confusable.restriction_level("abc\u3042")  # HIGHLY_RESTRICTIVE: Latin with Japanese
confusable.restriction_level(
    "p\u0430ypal"
)  # MINIMALLY_RESTRICTIVE: Latin with Cyrillic
confusable.is_mixed_script("p\u0430ypal")  # True

# Levels are ordered, most restrictive first:
confusable.restriction_level(name) <= confusable.RestrictionLevel.HIGHLY_RESTRICTIVE
```

`skeleton(text, direction)` takes the paragraph direction text is shown in:
`"ltr"` (the default, UTS #39's `skeleton`), `"rtl"`, `"auto"`, or `None` for
UTS #39's `internalSkeleton`, which ignores display order. Skeletons are for
comparison, not display, and change with the Unicode version
(`confusable.unicode_version`), so recompute any you store when it changes.

## What it is for

`confusable` decides whether user-supplied text is safe to accept as an identity: a
username, display name, project name, slug or filename. Planned for v1:

- **Look-alike detection** with the UTS #39 skeleton algorithm, so that `pаypal`
  (with a Cyrillic `а`) and `paypal` compare as confusable.
- **Restriction levels and mixed-script checks** from UTS #39 section 5, built on the
  Unicode `Scripts` and `Script_Extensions` properties.
- **Identifier status and type** from the UTS #39 General Security Profile.
- **Invisible and control characters**: default-ignorable code points, zero-width
  characters, bidirectional controls, and Tag-block "ASCII smuggling", while still
  accepting valid emoji tag sequences such as subdivision flags.
- **UAX #31 identifier checks** equivalent to Python 3.15's `unicodedata.isxidstart()`
  and `unicodedata.isxidcontinue()`, on Python 3.10 and later.
- **Grapheme clusters**: iteration and truncation that never split a user-perceived
  character, equivalent to Python 3.15's `unicodedata.iter_graphemes()`.
- **A compatibility module**, `confusable.compat.homoglyphs`, with the same API as
  `confusable_homoglyphs` 3.3.1, so existing code can switch by changing one import.

The Unicode data is pinned to a single Unicode version (18.0.0) and generated into the
package, so installing needs no network access and no compiler.

## Correctness

A look-alike that slips through is a security bug, so the tests come first. Every
operation is checked against two independent implementations of UTS #39, ICU and
the Rust `unicode-security` crate, over every Unicode code point and a corpus of
known attacks and generated strings. Both oracles run at the pinned Unicode
version, and every place where they differ is explained by a specific rule. See
[tools/oracles/README.md](tools/oracles/README.md).

## Development

```bash
uv sync
uv run pre-commit install
uv run pytest
uv run pre-commit run --all-files
```

[AGENTS.md](AGENTS.md) has the project's conventions, for people and coding agents
alike.

## Security

To report a vulnerability, see [SECURITY.md](.github/SECURITY.md).

## License

MIT. See [LICENSE](LICENSE). The Unicode data the package and its test fixtures are
generated from is under the Unicode License v3; see
[LICENSES/Unicode-3.0.txt](LICENSES/Unicode-3.0.txt).
