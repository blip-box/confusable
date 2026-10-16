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

Packaging, CI, and the conformance harness: oracle fixtures for every v1
operation and conformance tests that are strict xfails until the library
implements each operation. The `confusable` package itself only exposes
`__version__`; there is no Unicode data or detection code in it yet.

## Decisions

| Topic | Decision |
|---|---|
| Runtime dependencies | None. No C extensions. |
| Python | `>=3.10`. CI tests 3.10 to 3.15 on Linux and 3.15 on macOS and Windows. |
| License | MIT for the code. Unicode data files are under the Unicode License v3; ship that notice next to the generated data. |
| Unicode data | Generated Python tables are committed, so installs need no network. |
| Unicode version | 18.0.0, stored in one place and exposed as `confusable.unicode_version`. Today that place is `tools/unicode_sources.py`. |
| Specification | UTS #39 revision 34. Its `skeleton(X)` is `bidiSkeleton(LTR, X)`, which applies the Unicode Bidirectional Algorithm (UAX #9) before the confusable mapping. |
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

To regenerate the conformance fixtures, or check them as CI's `oracles` job does
(needs a C++ compiler and `cargo`; see `tools/oracles/README.md`):

```bash
uv run --no-project --python 3.14 python -m tools.oracles.generate
uv run --no-project --python 3.14 python -m tools.oracles.generate --check
```

## Layout

- `src/confusable/`: the package. It ships `py.typed`; mypy runs in strict mode.
- `tests/`: pytest and hypothesis.
- `tests/conformance/`: the conformance harness. `fixtures/` holds the generated
  oracle output, `attacks.py` the curated attack corpus, `oracle_data.py` reads
  the fixtures, and `adapter.py` maps each operation the specifications define to
  the library.
- `tools/unicode_sources.py`: the pinned Unicode source files, by SHA-256.
- `tools/oracles/`: the ICU and Rust oracles and the fixture generator.
- `LICENSES/Unicode-3.0.txt`: the license of the Unicode data the fixtures and
  tables derive from.
- `.github/workflows/ci.yml`: a `lint` job, the `test` matrix, an `oracles` job that
  regenerates the fixtures and fails on any difference, and a `required` job that
  fails unless all three succeed. Branch protection on `main` requires only
  `required`, so the jobs can change without touching repository settings.
- `.github/workflows/commit-lint.yml`: commitlint on the PR's commits and its title.
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
  the title becomes the commit on `main`; commitlint checks both.
- One PR per workstream, on a branch named `<type>/<topic>`, e.g. `feat/skeleton`.
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
  after 60 days without repository activity, is worse than none.

## Unicode data sources

All pinned to the same Unicode version, under `https://www.unicode.org/Public/<version>/`,
and listed with their hashes in `tools/unicode_sources.py`:

- `security/`: `confusables.txt`, `IdentifierStatus.txt`, `IdentifierType.txt`,
  `intentional.txt`, `confusablesSummary.txt`. Since Unicode 17 these live here, not
  under the older `Public/security/<version>/` tree, which stops at 16.0.0.
- `ucd/`: `UnicodeData.txt`, `Scripts.txt`, `ScriptExtensions.txt`,
  `DerivedCoreProperties.txt`, `DerivedNormalizationProps.txt`, `PropList.txt`,
  `PropertyValueAliases.txt`, `StandardizedVariants.txt`, `NormalizationTest.txt`,
  `auxiliary/GraphemeBreakProperty.txt`, `auxiliary/GraphemeBreakTest.txt`,
  `emoji/emoji-data.txt`
- `emoji/`: `emoji-sequences.txt` (valid tag sequences), `emoji-zwj-sequences.txt`

`bidiSkeleton` will also need `ucd/BidiMirroring.txt`, `ucd/BidiBrackets.txt` and
`ucd/extracted/DerivedBidiClass.txt`, with `ucd/BidiCharacterTest.txt` as its
conformance test; they are not pinned yet.

`unicode_sources.py` verifies each file's version as well as its hash, and the
formats differ: most `ucd/` files name it in the first line (`# Scripts-18.0.0.txt`),
the `security/` files and `ucd/emoji/emoji-data.txt` have a `# Version: 18.0.0` line,
the `emoji/` files have `# Version: 18.0`, and `UnicodeData.txt` has none, so only
its hash pins it.

## Roadmap

Each item is its own pull request:

1. Data pipeline: the generator, the committed tables, and a scheduled regeneration
   workflow that opens a PR when Unicode publishes a release.
2. Core API, one PR per module where sensible, each wiring its operations into
   `tests/conformance/adapter.py`.
3. `confusable.compat.homoglyphs`, with differential tests against
   `confusable_homoglyphs` 3.3.1.
4. First alpha on PyPI via trusted publishing.

## References

- UTS #39: https://www.unicode.org/reports/tr39/
- UAX #31: https://www.unicode.org/reports/tr31/
- UAX #29: https://www.unicode.org/reports/tr29/
- UAX #9: https://www.unicode.org/reports/tr9/
- ICU SpoofChecker: https://unicode-org.github.io/icu-docs/apidoc/dev/icu4c/classicu_1_1SpoofChecker.html
- Rust `unicode-security`: https://github.com/unicode-rs/unicode-security
