# Charter

What `confusable` is for, what it will and will not do, and the principles every
change is held to. This is the "why" behind [AGENTS.md](AGENTS.md), which holds
the "how".

Each clause has a stable ID. A request to change the library is accepted or
declined by citing, by ID, the clause it serves or breaks. A clause is amended
in place or retired with a dated note; it is never renumbered, and a retired
number is never reused. This file takes effect when a steward merges it, and
every change to it when a steward merges that change (C-GOV-4).

## Mission

**C-MISSION-1** `confusable` decides whether user-supplied text is safe to
accept as an identity: a username, display name, project name, slug or
filename.

**C-MISSION-2** A look-alike it misses, or an invisible character it lets
through, is a security bug in every project that relies on it. Correctness
comes before features, speed and convenience.

**C-MISSION-3** Relying on the library means trusting nothing beyond Python and
Unicode's own data: no runtime dependencies, no C extensions, no network at
install or run time.

## Scope

A feature is in scope when it serves C-MISSION-1 and Unicode's specifications
or data define its behaviour, so that it can be tested against them and
against an independent implementation. Version 1 is:

**C-SCOPE-1** Look-alike detection: the UTS #39 skeleton, and a two-string
comparison that says whether, and in which way, two strings are confusable.

**C-SCOPE-2** Mixed-script detection and restriction levels, UTS #39 sections
5.1 and 5.2.

**C-SCOPE-3** Identifier status and type under the General Security Profile,
and the UAX #31 `XID_Start` and `XID_Continue` checks.

**C-SCOPE-4** Mixed numbers and unlikely combining marks, UTS #39 sections 5.3
and 5.4, the hidden dot above included.

**C-SCOPE-5** Invisible and control characters: default-ignorable code points,
bidirectional controls and Tag-block "ASCII smuggling", while accepting the
emoji and variation sequences that give such a character a visible job.

**C-SCOPE-6** Grapheme clusters: iteration, and truncation that never splits
what a reader sees as one character, UAX #29.

**C-SCOPE-7** `confusable.compat.homoglyphs`, with the API and results of
`confusable_homoglyphs` 3.3.1, so that existing code switches by changing one
import.

**C-SCOPE-8** Anything else is a proposal. It is accepted only with the clause
it serves, named by ID, and the specification that defines its behaviour.

## Non-goals

**C-OUT-1** Transliteration, or any mapping of text to ASCII for display. Use
`anyascii`.

**C-OUT-2** Generating confusable variants of a string.

**C-OUT-3** Following the interpreter's Unicode version. Python's `unicodedata`
reflects whichever Unicode version the interpreter was built with (13.0 on
Python 3.10); the library answers from one pinned version on every Python.

## Specifications

**C-SPEC-1** Follow Unicode Technical Standard #39, Unicode Security
Mechanisms, exactly, at a pinned revision. Where the library deviates, the
reason stands in a comment next to the code and a test pins the behaviour.

**C-SPEC-2** The same holds for the other standards the library implements:
UAX #9 (the Bidirectional Algorithm, which the skeleton applies first), UAX #29
(grapheme clusters), UAX #31 (identifiers and Recommended scripts) and UTS #37
(ideographic variation sequences). `AGENTS.md` records the pinned revisions.

**C-SPEC-3** Canonically equivalent strings get the same answer. A check whose
result depends on whether text arrived as NFC or NFD is a bug, even where ICU
has it.

**C-SPEC-4** One Unicode version at a time, pinned by name and by the SHA-256 of
every source file, with the tables generated from those files and committed.
Moving to a new Unicode version is a deliberate change that a person makes
after reading the new specification revisions.

**C-SPEC-5** Where a specification or an oracle turns out to be wrong, the
library follows the correct behaviour, says so next to the code with a test,
and the finding is reported upstream.

## Correctness

**C-CORRECT-1** The test suite is the product. Every operation a specification
defines is checked against an independent implementation (ICU's SpoofChecker,
the Rust `unicode-security` crate, and `confusable_homoglyphs` for the compat
module) over every code point and a corpus of known attacks. Their outputs are
committed as fixtures, so an ordinary test run needs no ICU, Rust or network.

**C-CORRECT-2** Every difference from an oracle is explained by a specific rule
and pinned by a test. Oracles can be wrong: the specification wins, and the
oracle is patched so that the fixtures show the specification's answer.

**C-CORRECT-3** No change weakens the suite: no deleted test, no new skip or
expected failure to make a change pass, and no edited fixture or generated
table without the change to the generator or corpus that reproduces it.

**C-CORRECT-4** The library is written from the specifications. ICU and Rust
source may be read to diagnose a disagreement and to patch the oracles; it is
never reproduced in `src/`.

## API

**C-API-1** A result cannot be misread into a missed look-alike: "not
confusable" is `None`, never an object that happens to be false; enumerated
results are exclusive, so an equality test cannot miss a kind; ordered results
are numbered as the specification numbers them.

**C-API-2** Where the standard library has the same feature, the library
behaves like it: `iter_graphemes`, `isxidstart` and `isxidcontinue` match
Python 3.15's `unicodedata`, on every supported Python, at the pinned Unicode
version.

**C-API-3** What UTS #39 calls a modification of a profile is off by default
and named at the call, as `joining_controls=True` is.

**C-API-4** The compat module changes neither the names nor the results of the
API it copies, beyond correcting that package's data. New code is pointed to
the UTS #39 API.

## Platform

**C-PLAT-1** Pure Python, with no runtime dependencies and no C extensions.
Installing needs no compiler and no network.

**C-PLAT-2** Python 3.10 and later, tested on every current version on Linux,
and on the newest on macOS and Windows.

**C-PLAT-3** Importing the package is cheap: no generated table loads at
import, and nothing imports `inspect` or `ast` on the way.

**C-PLAT-4** MIT for the code. The Unicode data is under the Unicode License
v3, shipped with its notice.

## Security of the project

**C-SEC-1** Python source is ASCII; every other character is an escape. No
tracked file holds an invisible, bidirectional or other hidden character. The
files agents read as instructions (`AGENTS.md`, `CLAUDE.md` and this file) are
ASCII too, so that a look-alike cannot change what they say.

**C-SEC-2** Everything the build trusts is pinned: Unicode source files by
SHA-256, GitHub Actions by commit SHA, tool versions by floors that a re-lock
cannot lower, and the generated tables committed, so that installing and
testing need no network.

**C-SEC-3** Vulnerability reports arrive through GitHub's private reporting and
are handled by the stewards. Nothing is public before the advisory is.

## Governance

**C-GOV-1** At most three stewards own this charter, the direction of the
library and its risk. A steward approves every code change and runs every
release. Nothing merges without one.

**C-GOV-2** Agents do the routine work: triage, planning, building, review and
release proposals, under `AGENTS.md` and, once Guild runs on this repository,
`GUILD.md`. Every agent comment says that it comes from Guild and links its
decision record.

**C-GOV-3** Contributors take part through issues and comments. A bug report is
accepted with a reproducer that the oracle check confirms and a citation of
the specification clause or the oracle. A feature request names the clause it
serves; one that serves no clause is declined, naming the nearest.

**C-GOV-4** Changing this file is a tier 2 change: agents may draft it, a
steward commits it, and two stewards approve it. While there is one steward,
that steward's approval, a public notice of 24 hours and the Reviewer's
no-objection stand in for the second approval, and the record says so.

## Enforcement

A clause earns its keep where something checks it. This table lists the checks
that exist today, and `tests/test_charter.py` checks that each path it names
still does.

| Clause | Checked by |
|---|---|
| C-SPEC-1, C-SPEC-2, C-CORRECT-1 | `tests/conformance/test_conformance.py` against the committed fixtures, `tests/conformance/attacks.py` |
| C-SPEC-3 | `tests/test_identifiers.py`, `tests/test_joining.py`, `tests/test_marks.py`, `tests/test_invisible.py` |
| C-SPEC-4 | `tools/unicode_sources.py` (hashes), `tools/generate_tables.py` with --check and `tools/oracles/generate.py` with --check in CI's generated job, `tests/test_unicode_release.py` |
| C-CORRECT-2 | `tools/oracles/icu/patches/`, `tests/conformance/test_fixtures.py` |
| C-API-2 | `tests/test_graphemes.py`, `tests/test_identifiers.py` |
| C-API-4 | `tests/test_homoglyphs.py` against `tests/conformance/fixtures/homoglyphs.txt.gz` |
| C-PLAT-1, C-PLAT-3 | `tests/test_package.py` |
| C-PLAT-2 | the test matrix in `.github/workflows/ci.yml` |
| C-SEC-1 | `tests/test_source_hygiene.py`, ruff's PLE25 rules, `tests/test_charter.py` |
| C-SEC-2 | `tools/unicode_sources.py`, zizmor in `.pre-commit-config.yaml`, `.github/dependabot.yml` |
| C-SEC-3 | `.github/SECURITY.md` |
| C-GOV-4 | this file is on the list of paths agents cannot change; the rest waits for Guild |

Not checked by anything yet: C-CORRECT-3 (a plain check in the Guild harness
will fail on deleted tests, new skips or expected failures, and fixture or
table edits without a generator change) and C-GOV-1 (the steward limit is a
repository setting).
