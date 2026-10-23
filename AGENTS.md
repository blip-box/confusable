# AGENTS.md

Instructions for coding agents and human contributors. Keep this file true: when a
change makes a statement here wrong, fix this file in the same pull request.

## Project

`confusable` is a pure-Python library that decides whether user-supplied text is safe
to accept as an identity: a username, display name, project name, slug or filename. It
implements Unicode Technical Standard #39 (Unicode Security Mechanisms): look-alike
detection via the skeleton algorithm, restriction levels and mixed-script checks. It
also detects invisible and direction-control characters (including Tag-block "ASCII
smuggling"), offers grapheme-safe truncation, and ships `confusable.compat.homoglyphs`
with the API of `confusable_homoglyphs` 3.3.1.

## Current state

Packaging, CI, the conformance harness, generated Unicode tables for every v1
feature, NFD, the Unicode Bidirectional Algorithm, and look-alike detection: the
public `skeleton()`, `match()` and `Match`, which pass their conformance tests.
Restriction levels, identifier checks, invisible characters and graphemes are
not written yet; their conformance tests are strict xfails.

## Decisions

| Topic | Decision |
|---|---|
| Runtime dependencies | None. No C extensions. |
| Tooling security floors | `required-version = ">=0.13.4"` for uv and `virtualenv>=21.14.13` in the lint group, after the October 2026 eMudhra/emSign CA compromise: older uv and the pip that older virtualenv seeds into pre-commit hooks still trust the compromised root. Keep floors (`>=`) for such fixes so a re-lock cannot regress. CI runs no Node except the runner's own, which GitHub patches. |
| Python | `>=3.10`. CI tests 3.10 to 3.15 on Linux and 3.15 on macOS and Windows. |
| License | MIT for the code. Unicode data files are under the Unicode License v3; ship that notice next to the generated data. |
| Unicode data | Generated Python tables are committed, so installs need no network. |
| Unicode version | 18.0.0, pinned in `tools/unicode_sources.py`; the table generator copies it into `confusable._data`, and the package exposes it as `confusable.unicode_version`. |
| New Unicode versions | A weekly workflow opens an issue with the checklist, rather than a PR: the move needs a person to read the new spec revisions and an ICU release for the oracles, which usually ships weeks after Unicode. `python -m tools.unicode_release prepare VERSION` does the mechanical part. |
| Specification | UTS #39 revision 34. Its `skeleton(X)` is `bidiSkeleton(LTR, X)`, which applies the Unicode Bidirectional Algorithm (UAX #9 revision 52) before the confusable mapping. v1 implements the full algorithm. |
| Bidi fast path | UTS #39 says left-to-right text without R or AL characters keeps its order. That is wrong: a shortcut must also rule out AN, RLE, RLO and RLI (see `src/confusable/_bidi.py`). |
| Look-alike API | `skeleton(text, direction="ltr")`, where `direction` is `"ltr"`, `"rtl"`, `"auto"` (UTS #39's FS) or `None` for internalSkeleton; and `match(a, b, direction="ltr")`, which returns a `Match` flag: `SINGLE_SCRIPT`, or `MIXED_SCRIPT` with `WHOLE_SCRIPT` when both strings are single-script, and an empty, false `Match(0)` when the strings are not confusable. |
| v1 scope | `skeleton()`, a two-string comparison (do not call it `is_confusable()` on a module named `confusable`), restriction levels, mixed-script detection, identifier status and type, invisible and control characters, UAX #31 `isxidstart`/`isxidcontinue` equivalents, grapheme iteration and safe truncation, and the compat module. |
| Out of scope | Transliteration (use `anyascii`), generating confusable variants. |

## Commands

```bash
uv sync                            # create .venv with the dev dependencies
uv run pre-commit install          # install the pre-commit and commit-msg hooks
uv run pytest                      # run the tests
uv run pre-commit run --all-files  # ruff, mypy, zizmor, actionlint, uv-lock, file hygiene
```

CI runs exactly these, so a clean local run means a clean CI run. The actionlint hook
downloads its own Go toolchain on first run.

To regenerate the package's data tables in `src/confusable/_data/`, or check them:

```bash
uv run python -m tools.generate_tables
uv run python -m tools.generate_tables --check
```

To regenerate the conformance fixtures, or check them (needs a C++ compiler and
`cargo`; see `tools/oracles/README.md`):

```bash
uv run --no-project --python 3.14 python -m tools.oracles.generate
uv run --no-project --python 3.14 python -m tools.oracles.generate --check
```

CI's `generated` job runs both checks.

## Layout

- `src/confusable/`: the package. It ships `py.typed`; mypy runs in strict mode.
- `src/confusable/_skeleton.py`: `skeleton`, `match` and `Match` (UTS #39 section 4).
- `src/confusable/_scripts.py`: augmented and resolved script sets (section 5.1).
- `src/confusable/_bidi.py`: the Unicode Bidirectional Algorithm, for bidiSkeleton.
- `src/confusable/_normalize.py`: NFD on the generated tables.
- `src/confusable/_lookup.py`: lookups in the generated runs and ranges.
- `src/confusable/_data/`: generated Unicode tables, one module per area (bidi,
  confusables, emoji, graphemes, identifiers, normalization, properties,
  scripts). Never edit them by hand; ruff skips them.
- `tools/generate_tables.py`: writes `src/confusable/_data/` from the pinned sources.
- `tools/unicode_release.py`: notices new Unicode releases and re-pins the sources.
- `tests/`: pytest and hypothesis.
- `tests/conformance/`: the conformance harness. `fixtures/` holds the generated
  oracle output, `attacks.py` the curated attack corpus, `oracle_data.py` reads
  the fixtures, and `adapter.py` maps each operation the specifications define to
  the library.
- `tools/unicode_sources.py`: the pinned Unicode source files, by SHA-256.
- `tools/oracles/`: the ICU and Rust oracles and the fixture generator.
- `LICENSES/Unicode-3.0.txt`: the license of the Unicode data the fixtures and
  tables derive from.
- `.github/workflows/ci.yml`: a `lint` job, the `test` matrix, a `generated` job that
  regenerates the data tables and the fixtures and fails on any difference, a
  `scheduled` job that fails while a scheduled workflow is disabled, and a
  `required` job that fails unless all of them succeed. Branch protection on
  `main` requires only `required`, so the jobs can change without touching
  repository settings.
- `.github/workflows/unicode-release.yml`: the weekly check for new Unicode
  releases. It opens an issue for a new release, and opens or comments on an
  issue when it fails.
- `.github/workflows/commit-lint.yml`: checks that the PR title is a Conventional
  Commit. The commit-msg hook checks individual commits locally.
- `.github/workflows/dependabot-auto-merge.yml`: auto-merge for non-major Dependabot PRs.
- `.github/dependabot.yml`: weekly updates for uv, GitHub Actions and pre-commit
  hooks, with a seven-day cooldown on new releases.

## Rules

### Correctness

- A missed look-alike is a security bug. The test suite is the product.
- Build the conformance harness before the public API. Oracles are ICU's SpoofChecker
  and the Rust `unicode-security` crate. Commit their outputs as fixtures so ordinary
  test runs need no ICU, Rust or network.
- Follow UTS #39 exactly. Where the library deviates, explain why in a comment next to
  the code and pin the behaviour with a test.
- Never edit generated tables or fixtures by hand. Change the generator, the corpus
  or the oracles and regenerate; CI fails on fixtures that a fresh run does not
  reproduce.
- Do not use Python's `unicodedata` for data the specifications define: it follows
  the interpreter's Unicode version (13.0 on Python 3.10), not the pinned one.
- Conformance tests reach the library only through `tests/conformance/adapter.py`.
  To implement an operation, wire its adapter function and remove the matching
  `not_implemented` markers; strict xfail fails the suite until both are done.

### Git and pull requests

- Conventional Commits for every commit and every PR title. PRs are squash-merged, so
  the title becomes the commit on `main`; CI checks the title, and the commit-msg
  hook (commitlint) checks commits locally.
- One PR per workstream, on a branch named `<type>/<topic>`, e.g. `feat/skeleton`.
- The version lives in `pyproject.toml` and, as a literal, in
  `src/confusable/__init__.py` (reading it from package metadata would add about
  100 ms to every import). Change both; `tests/test_package.py` checks they match.
- The maintainer merges. Agents do not merge PRs and do not work around tooling that
  blocks a merge; ask instead.

### GitHub Actions

- Pin every action to a full commit SHA with the version in a trailing comment.
  Dependabot keeps the pins current.
- Set `permissions: {}` at the workflow level and grant scopes per job, with a comment
  on each scope the pedantic zizmor persona asks about.
- Check out with `persist-credentials: false`.
- Never interpolate untrusted text (PR titles, issue bodies, branch names, model output)
  into a `run:` step. Pass it through `env:` and files such as `--body-file`. `gh` needs
  `GH_REPO` when the job has no checkout.
- Keep `uvx zizmor --persona=pedantic .` free of findings.
- Do not add a scheduled workflow unless failures reach a human, for example by
  opening an issue. A scheduled workflow that fails silently, or that GitHub disables
  after 60 days without repository activity, is worse than none. Add every
  scheduled workflow to the `scheduled` job in `ci.yml`, which fails while one is
  disabled.

## Unicode data sources

All pinned to the same Unicode version, under `https://www.unicode.org/Public/<version>/`,
and listed with their hashes in `tools/unicode_sources.py`:

- `security/`: `confusables.txt`, `IdentifierStatus.txt`, `IdentifierType.txt`,
  `intentional.txt`, `confusablesSummary.txt`. Since Unicode 17 these live here, not
  under the older `Public/security/<version>/` tree, which stops at 16.0.0.
- `ucd/`: `UnicodeData.txt`, `Scripts.txt`, `ScriptExtensions.txt`,
  `DerivedCoreProperties.txt`, `DerivedNormalizationProps.txt`, `PropList.txt`,
  `PropertyValueAliases.txt`, `StandardizedVariants.txt`, `NormalizationTest.txt`,
  `BidiBrackets.txt`, `BidiMirroring.txt`, `BidiTest.txt`, `BidiCharacterTest.txt`,
  `extracted/DerivedBidiClass.txt`, `auxiliary/GraphemeBreakProperty.txt`,
  `auxiliary/GraphemeBreakTest.txt`, `emoji/emoji-data.txt`
- `emoji/`: `emoji-sequences.txt` (valid tag sequences), `emoji-zwj-sequences.txt`

Some files give defaults for unassigned code points in `# @missing:` lines rather
than data lines (`DerivedBidiClass.txt` assigns R and AL by block this way); the
generator must apply them before the data lines.

`unicode_sources.py` verifies each file's version as well as its hash, and the
formats differ: most `ucd/` files name it in the first line (`# Scripts-18.0.0.txt`),
the `security/` files and `ucd/emoji/emoji-data.txt` have a `# Version: 18.0.0` line,
the `emoji/` files have `# Version: 18.0`, and `UnicodeData.txt` has none, so only
its hash pins it.

## Roadmap

Each item is its own pull request:

1. Core API, one PR per module where sensible, each wiring its operations into
   `tests/conformance/adapter.py`: scripts and restriction levels (built on
   `_scripts.py`), identifiers, invisible characters, graphemes. Skeletons and
   `match` are done.
2. `confusable.compat.homoglyphs`, with differential tests against
   `confusable_homoglyphs` 3.3.1.
3. First alpha on PyPI via trusted publishing.

## References

- UTS #39: https://www.unicode.org/reports/tr39/
- UAX #31: https://www.unicode.org/reports/tr31/
- UAX #29: https://www.unicode.org/reports/tr29/
- UAX #9: https://www.unicode.org/reports/tr9/
- ICU SpoofChecker: https://unicode-org.github.io/icu-docs/apidoc/dev/icu4c/classicu_1_1SpoofChecker.html
- Rust `unicode-security`: https://github.com/unicode-rs/unicode-security
