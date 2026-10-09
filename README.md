# confusable

Unicode spoofing and confusable detection for Python, following
[Unicode Technical Standard #39](https://www.unicode.org/reports/tr39/). Pure Python,
no runtime dependencies.

> **Status: pre-alpha.** This repository contains only the project scaffold. Nothing
> is on PyPI yet, and the features below are planned, not implemented.

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

MIT. See [LICENSE](LICENSE). The Unicode data files the package is generated from are
under the [Unicode License v3](https://www.unicode.org/license.txt); that notice will
ship alongside the generated data.
