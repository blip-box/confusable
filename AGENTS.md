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

Scaffold only: packaging, an empty `confusable` package that exposes `__version__`,
smoke tests, linters and CI. There is no Unicode data and no detection code yet.

## Decisions

| Topic | Decision |
|---|---|
| Runtime dependencies | None. No C extensions. |
| Python | `>=3.10`. CI tests 3.10 to 3.15 on Linux and 3.15 on macOS and Windows. |
| License | MIT for the code. Unicode data files are under the Unicode License v3; ship that notice next to the generated data. |
| Unicode data | Generated Python tables are committed, so installs need no network. |
| Unicode version | 18.0.0, stored in one place and exposed as `confusable.unicode_version`. |
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

## Layout

- `src/confusable/`: the package. It ships `py.typed`; mypy runs in strict mode.
- `tests/`: pytest and hypothesis.
- `.github/workflows/ci.yml`: a `lint` job, the `test` matrix, and a `required` job
  that fails unless both succeed. Branch protection on `main` should require only
  `required`, so the matrix can change without touching repository settings.
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
- Never edit generated tables by hand. Change the generator and regenerate.

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

All pinned to the same Unicode version, under `https://www.unicode.org/Public/<version>/`:

- `security/`: `confusables.txt`, `IdentifierStatus.txt`, `IdentifierType.txt`,
  `intentional.txt`, `confusablesSummary.txt`. Since Unicode 17 these live here, not
  under the older `Public/security/<version>/` tree, which stops at 16.0.0.
- `ucd/`: `Scripts.txt`, `ScriptExtensions.txt`, `DerivedCoreProperties.txt`,
  `PropList.txt`, `auxiliary/GraphemeBreakProperty.txt`,
  `auxiliary/GraphemeBreakTest.txt`, `emoji/emoji-data.txt`
- `emoji/emoji-sequences.txt` (valid tag sequences)

The generator must verify each file's version against the pinned one, and the formats
differ: most `ucd/` files name it in the first line (`# Scripts-18.0.0.txt`), the
`security/` files and `ucd/emoji/emoji-data.txt` have a `# Version: 18.0.0` line, and
`emoji/emoji-sequences.txt` has `# Version: 18.0`.

## Roadmap

Each item is its own pull request:

1. Conformance harness and oracle fixtures.
2. Data pipeline: the generator, the committed tables, and a scheduled regeneration
   workflow that opens a PR when Unicode publishes a release.
3. Core API, one PR per module where sensible.
4. `confusable.compat.homoglyphs`, with differential tests against
   `confusable_homoglyphs` 3.3.1.
5. First alpha on PyPI via trusted publishing.

## References

- UTS #39: https://www.unicode.org/reports/tr39/
- UAX #31: https://www.unicode.org/reports/tr31/
- UAX #29: https://www.unicode.org/reports/tr29/
- ICU SpoofChecker: https://unicode-org.github.io/icu-docs/apidoc/dev/icu4c/classicu_1_1SpoofChecker.html
- Rust `unicode-security`: https://github.com/unicode-rs/unicode-security
