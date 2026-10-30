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

[CHARTER.md](CHARTER.md) says why: the mission, scope, non-goals and principles
as numbered clauses (`C-SPEC-1`). This file says how. Cite a clause by ID when
accepting or declining a request; a change to the charter needs a steward.
Routine maintenance runs under Guild, the agent harness in
[blip-box/guild](https://github.com/blip-box/guild); `guild.toml` configures it.

## Current state

Packaging, CI, the conformance harness, generated Unicode tables for every v1
feature, NFD, the Unicode Bidirectional Algorithm, look-alike detection
(`skeleton()`, `match()`, `Match`) and mixed-script detection with restriction
levels (`is_mixed_script()`, `restriction_level()`, `RestrictionLevel`), the
identifier checks (`is_allowed()`, `identifier_status()`, `identifier_types()`,
`isxidstart()`, `isxidcontinue()`), NFC, and the mixed-number and combining-mark
checks (`has_mixed_numbers()`, `has_unlikely_marks()`, `has_hidden_overlay()`),
and grapheme clusters (`iter_graphemes()`, `Segment`, `truncate()`), all passing
their conformance tests; and the joining-control contexts of section 3.1.1.1
(`is_allowed(text, joining_controls=True)`) and invisible and control characters
(`find_invisible()`, `has_invisible()`, `Invisible`), which no oracle implements.
The core API is complete: no conformance test is an xfail. So is
`confusable.compat.homoglyphs`, which is checked against confusable_homoglyphs
3.3.1 itself. The first alpha on PyPI is next.

## Decisions

| Topic | Decision |
|---|---|
| Runtime dependencies | None. No C extensions. |
| Tooling security floors | `required-version = ">=0.13.4"` for uv and `virtualenv>=21.14.13` in the lint group, after the October 2026 eMudhra/emSign CA compromise: older uv and the pip that older virtualenv seeds into pre-commit hooks still trust the compromised root. Keep floors (`>=`) for such fixes so a re-lock cannot regress. CI runs no Node except the runner's own, which GitHub patches. |
| Python | `>=3.10`. CI tests 3.10 to 3.15 on Linux and 3.15 on macOS and Windows. |
| License | MIT for the code. Unicode data files are under the Unicode License v3; ship that notice next to the generated data. |
| Unicode data | Generated Python tables are committed, so installs need no network. |
| Import time | `import confusable` loads no generated table: each module loads the tables it needs on first use, through `functools.cache` functions that import from `confusable._data` (see `_identifiers.py`). Without cached bytecode (`PYTHONDONTWRITEBYTECODE=1`, read-only installs) the tables take about 100 ms to import. No dataclasses or `NamedTuple` either: they import `inspect` and `ast`, or `annotationlib` on Python 3.14, which costs milliseconds. `tests/test_package.py` checks both in a fresh interpreter. |
| Unicode version | 18.0.0, pinned in `tools/unicode_sources.py`; the table generator copies it into `confusable._data`, and the package exposes it as `confusable.unicode_version`. |
| New Unicode versions | A weekly workflow opens an issue with the checklist, rather than a PR: the move needs a person to read the new spec revisions and an ICU release for the oracles, which usually ships weeks after Unicode. `python -m tools.unicode_release prepare VERSION` does the mechanical part. |
| Specification | UTS #39 revision 34. Its `skeleton(X)` is `bidiSkeleton(LTR, X)`, which applies the Unicode Bidirectional Algorithm (UAX #9 revision 52) before the confusable mapping. v1 implements the full algorithm. |
| Bidi fast path | UTS #39 says left-to-right text without R or AL characters keeps its order. That is wrong: a shortcut must also rule out AN, RLE, RLO and RLI (see `src/confusable/_bidi.py`). |
| Look-alike API | `skeleton(text, direction="ltr")`, where `direction` is `"ltr"`, `"rtl"`, `"auto"` (UTS #39's FS) or `None` for internalSkeleton; and `match(a, b, direction="ltr")`, which returns `None` when the strings are not confusable and otherwise one `Match`: `SINGLE_SCRIPT`, `MIXED_SCRIPT` or `WHOLE_SCRIPT`. The values are exclusive, and `Match.mixed_script` is true for both mixed kinds. `None` rather than a false object, so `is not None` checks are safe, and exclusive values so `==` cannot miss whole-script spoofs. |
| Restriction levels | `restriction_level(text)` returns a `RestrictionLevel` IntEnum numbered as in UTS #39 (ASCII_ONLY=1 to UNRESTRICTED=6), so lower is more restrictive. The identifier profile is the General Security Profile. Step 7's Recommended scripts are UAX #31 revision 45 Table 5, kept in `_restriction.py` because no data file lists them; Bopomofo has been Limited Use since Unicode 17. |
| Identifier profile | The General Security Profile (Identifier_Status=Allowed) under canonical equivalence, as UTS #39 section 3.1 says: each normalization segment passes if it is all Allowed in its NFD or its NFC form, so the answer does not depend on how the text is encoded. ICU and Rust test the characters as written; ICU patch 0006 makes the oracle follow the spec. `restriction_level` step 1 uses the same test. |
| Joining controls | ZWJ and ZWNJ are outside the General Security Profile, as in UTS #39, ICU and Rust. `is_allowed` and `restriction_level` take `joining_controls=True` to allow them in the contexts A1, A2 and B of section 3.1.1.1 only, tested on the NFC form with "single script" meaning a non-empty resolved script set (section 5.1). UTS #39 calls this a modification of the profile, so it is opt-in. No oracle implements the contexts: `tests/test_joining.py` checks the spec's figures, invariance under normalization, and that the contexts are narrower than IDNA2008's CONTEXTJ, as the spec says, except where a mark sits between the virama and the joining control, which A2 and B allow and CONTEXTJ does not. |
| Numbers and marks | `has_mixed_numbers` is section 5.3. `has_unlikely_marks` is both of section 5.4's mark rules: a run of nonspacing marks (gc=Mn or Me) that repeats a mark, as ICU's INVISIBLE check finds, or has more than four, which ICU does not check. `has_hidden_overlay` is ICU's HIDDEN_OVERLAY, the only implementation of the 5.4 overlay rule. The mark checks test the NFD form, as Unicode conformance clause C6 asks; ICU tests overlays as written, so NFC text slipped through, and ICU patch 0007 makes the oracle use NFD. A consequence: U+0130, whose NFD is I and a dot above, is a hidden overlay, because I's prototype is l. |
| Invisible characters | `find_invisible(text)` returns `(index, Invisible)` pairs for every Default_Ignorable_Code_Point and C0 or C1 control, except where the context gives the character a visible job: ZWJ and ZWNJ in the section 3.1.1.1 contexts, ZWJ joining two emoji (UAX #29 rule GB11, so emoji ZWJ sequences that are not RGI pass too; they hide nothing, and skeletons ignore ZWJ), Tag characters inside an RGI emoji tag sequence only (other subdivision flags show as a black flag with hidden text), and one variation selector completing a standardized or emoji variation sequence, or an ideographic variation sequence as UTS #37 defines it (VS17 to VS256 after a unified ideograph; the Ideographic Variation Database is not pinned, so registration is not checked). Contexts are judged on the NFC form: candidates are never changed or moved by normalization, so the n-th candidate of the NFC form is the n-th of the text. `tests/test_invisible.py` checks every RGI emoji sequence, from the `emoji-sequences.txt` fixture. |
| Graphemes | `iter_graphemes(text, start=0, end=sys.maxsize, /)` behaves like Python 3.15's `unicodedata.iter_graphemes`: it segments `text[start:end]`, with slice semantics, as a string of its own, and yields immutable `Segment`s with `start`, `end` and `str()`. It follows UAX #29 revision 49 (Unicode 18) on every Python, including its new rule GB9c, `Linker Extend* x Consonant`, so on Python 3.15 (Unicode 17) the two differ for text with an Indic linker and for characters whose properties changed; `tests/test_graphemes.py` compares them everywhere else. `truncate(text, max_graphemes, *, max_code_points, max_utf8_bytes, max_utf16_units)` keeps whole clusters within every given limit, because UAX #29 section 3 notes that a grapheme count does not bound data size. |
| Compat module | `confusable.compat.homoglyphs` has the modules `categories` and `confusables` of confusable_homoglyphs 3.3.1, with its functions, signatures, results and lazily built `categories_data` and `confusables_data`. Its data is rebuilt from the pinned Unicode files by that package's own rules, except that the confusable pairs come from the code point fields of confusables.txt: the package's generator reads them from the comments, which wrap right-to-left characters in LEFT-TO-RIGHT MARKs (so its data misses every Arabic and Hebrew look-alike) and show four space-like characters, HANGUL FILLER among them, as blanks it cannot parse. Results hold fresh lists. No command line and no CONFUSABLE_DATA. The oracle is the real package, installed by hash into `tools/oracles/homoglyphs/.build/`. |
| v1 scope | `skeleton()`, a two-string comparison (do not call it `is_confusable()` on a module named `confusable`), restriction levels, mixed-script detection, identifier status and type, invisible and control characters, UAX #31 `isxidstart`/`isxidcontinue` equivalents, grapheme iteration and safe truncation, and the compat module. |
| Out of scope | Transliteration (use `anyascii`), generating confusable variants. |
| Guild | The shell in `blip-box/guild`, pinned by commit in the repository variable `GUILDKIT_REF`. `guild.toml` holds the stewards, the risk tiers with the reject list of files agents may not change, and the pinned models with their prices; changing it is tier 2. `.github/workflows/guild-triage.yml` is the shell's template, copied; `tools/guild_oracle_check.py` answers whether the committed fixtures confirm a bug report's reproducer (`confirms`, `disagrees`, `not_applicable`, `not_run`, `error`); the issue forms give it its fields. Agents comment as the Triage App and cite `CHARTER.md` clauses by ID. Shadow mode: nothing merges without a steward. |

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

- `guild.toml`: the Guild configuration (see Decisions). `.github/CODEOWNERS`
  makes the stewards owners of every path, so that "require review from code
  owners" mirrors the tiers; `.github/ISSUE_TEMPLATE/`: the bug, feature and
  question forms the triage reads; `.github/workflows/guild-triage.yml`: the
  triage workflow; `tools/guild_oracle_check.py`: the oracle check, tested by
  `tests/test_guild_oracle_check.py`.
- `CHARTER.md`: the project's mission, scope, non-goals and principles as
  numbered clauses. `tests/test_charter.py` checks that clause IDs stay unique
  and consecutive, that every path its enforcement table names exists, and
  that `AGENTS.md`, `CLAUDE.md` and `CHARTER.md` are ASCII.
- `src/confusable/`: the package. It ships `py.typed`; mypy runs in strict mode.
- `src/confusable/_skeleton.py`: `skeleton`, `match` and `Match` (UTS #39 section 4).
- `src/confusable/_scripts.py`: augmented and resolved script sets (section 5.1).
- `src/confusable/_restriction.py`: `is_mixed_script`, `restriction_level` and
  `RestrictionLevel` (sections 5.1 and 5.2).
- `src/confusable/_numbers.py`: `has_mixed_numbers` (section 5.3).
- `src/confusable/_marks.py`: `has_unlikely_marks` and `has_hidden_overlay`
  (section 5.4).
- `src/confusable/_identifiers.py`: the General Security Profile, Identifier_Status
  and Identifier_Type, XID_Start and XID_Continue.
- `src/confusable/_joining.py`: the joining-control contexts (section 3.1.1.1).
- `src/confusable/_invisible.py`: `find_invisible`, `has_invisible` and `Invisible`.
- `src/confusable/_graphemes.py`: `iter_graphemes`, `Segment` and `truncate`
  (UAX #29).
- `src/confusable/_bidi.py`: the Unicode Bidirectional Algorithm, for bidiSkeleton.
- `src/confusable/_normalize.py`: NFD and NFC on the generated tables.
- `src/confusable/_lookup.py`: lookups in the generated runs and ranges.
- `src/confusable/_data/`: generated Unicode tables, one module per area (bidi,
  confusables, emoji, graphemes, homoglyphs, identifiers, joining, normalization,
  properties, scripts, variation). Never edit them by hand; ruff skips them.
- `tools/generate_tables.py`: writes `src/confusable/_data/` from the pinned sources.
- `tools/unicode_release.py`: notices new Unicode releases and re-pins the sources.
- `tests/`: pytest and hypothesis.
- `tests/conformance/`: the conformance harness. `fixtures/` holds the generated
  oracle output, `attacks.py` the curated attack corpus, `oracle_data.py` reads
  the fixtures, and `adapter.py` maps each operation the specifications define to
  the library.
- `tools/unicode_sources.py`: the pinned Unicode source files, by SHA-256.
- `src/confusable/compat/homoglyphs/`: the confusable_homoglyphs 3.3.1 API.
- `tools/oracles/`: the ICU, Rust and confusable_homoglyphs oracles and the fixture
  generator.
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
- `.github/workflows/dependabot-auto-merge.yml`: auto-merge for non-major Dependabot PRs,
  except updates to Anthropic or Claude tooling, which a human reviews. Keep
  Dependabot security updates off while this runs: they skip the cooldown, so a
  just-published release would merge on CI alone.
- `.github/dependabot.yml`: weekly updates for uv, GitHub Actions and pre-commit
  hooks, with a seven-day cooldown on new releases.

## Rules

### Correctness

- A missed look-alike is a security bug. The test suite is the product.
- Build the conformance harness before the public API. Oracles are ICU's SpoofChecker
  and the Rust `unicode-security` crate, and confusable_homoglyphs 3.3.1 for the
  compat module. Commit their outputs as fixtures so ordinary test runs need no
  ICU, Rust or network.
- Follow UTS #39 exactly. Where the library deviates, explain why in a comment next to
  the code and pin the behaviour with a test.
- Never edit generated tables or fixtures by hand. Change the generator, the corpus
  or the oracles and regenerate; CI fails on fixtures that a fresh run does not
  reproduce.
- Python source is ASCII. Write every other character as an escape (`"p\u0430ypal"`),
  so no look-alike, invisible or bidirectional character can hide in the code; other
  tracked files may use visible non-ASCII characters but none of those, except
  `AGENTS.md`, `CLAUDE.md` and `CHARTER.md`, which agents read as instructions
  and which are ASCII too. `tests/test_source_hygiene.py`, ruff's `PLE25` rules
  and `tests/test_charter.py` enforce this. Agents: a
  `\u` escape written in a tool parameter can reach the file as the literal
  character, so check the bytes after writing one.
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
- When a PR is stacked on another, retarget it to `main` before deleting the base
  branch: deleting the base first closes the stacked PR, and a closed PR cannot be
  retargeted.
- The version lives in `pyproject.toml` and, as a literal, in
  `src/confusable/__init__.py` (reading it from package metadata would add about
  100 ms to every import). Change both; `tests/test_package.py` checks they match.
- The maintainer merges. Agents do not merge PRs and do not work around tooling that
  blocks a merge; ask instead.
- The files on `guild.toml`'s reject list (`.github/**`, `.claude/**`, `CLAUDE.md`,
  `AGENTS.md`, `CHARTER.md`, `guild.toml`, `conftest.py`, `.pre-commit-config.yaml`)
  instruct or run the harness. Agents draft changes to them; a steward commits.

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
  `extracted/DerivedBidiClass.txt`, `extracted/DerivedJoiningType.txt`,
  `IndicSyllabicCategory.txt`, `auxiliary/GraphemeBreakProperty.txt`,
  `auxiliary/GraphemeBreakTest.txt`, `emoji/emoji-data.txt`,
  `emoji/emoji-variation-sequences.txt`
- `emoji/`: `emoji-sequences.txt` (valid tag sequences), `emoji-zwj-sequences.txt`

Some files give defaults for unassigned code points in `# @missing:` lines rather
than data lines (`DerivedBidiClass.txt` assigns R and AL by block this way, and
`DerivedJoiningType.txt` names its default by its long name, Non_Joining); the
generator must apply them before the data lines.

`unicode_sources.py` verifies each file's version as well as its hash, and the
formats differ: most `ucd/` files name it in the first line (`# Scripts-18.0.0.txt`),
the `security/` files and `ucd/emoji/emoji-data.txt` have a `# Version: 18.0.0` line,
the `emoji/` files have `# Version: 18.0`, and `UnicodeData.txt` has none, so only
its hash pins it.

## Roadmap

Each item is its own pull request:

1. First alpha on PyPI via trusted publishing.

Done: skeletons and `match`, mixed scripts and restriction levels,
identifiers, joining controls, invisible characters, the section 5.3 and 5.4
checks, graphemes, and `confusable.compat.homoglyphs`.

## References

- UTS #39: https://www.unicode.org/reports/tr39/
- UAX #31: https://www.unicode.org/reports/tr31/
- UAX #29: https://www.unicode.org/reports/tr29/
- UAX #9: https://www.unicode.org/reports/tr9/
- ICU SpoofChecker: https://unicode-org.github.io/icu-docs/apidoc/dev/icu4c/classicu_1_1SpoofChecker.html
- Rust `unicode-security`: https://github.com/unicode-rs/unicode-security
