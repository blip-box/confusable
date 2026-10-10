# Conformance oracles

The conformance fixtures in `tests/conformance/fixtures/` come from two
independent implementations of UTS #39, run over every code point and over a
corpus of strings. Ordinary test runs only read the committed fixtures; nothing
here runs unless you regenerate them.

## Regenerating

```bash
uv run --no-project --python 3.14 python -m tools.oracles.generate
uv run --no-project --python 3.14 python -m tools.oracles.generate --check
```

The first command rewrites the fixtures. The second compares a fresh run with
the committed ones, which is what the `oracles` job in CI does. Both need Python
3.12 or later, a C++17 compiler, `cargo`, `curl` and `patch`. The first run
builds ICU from source, which takes a minute or a few; later runs reuse it.

Every download is pinned: the Unicode files by SHA-256 and version header
(`tools/unicode_sources.py`), the ICU source release by SHA-256
(`icu/build.sh`), and the Rust crates by their crates.io checksums
(`rust_regen.py`).

## The oracles

**ICU** (primary). ICU 79.1, built from the 79.1rc source release, which
implements Unicode 18. The fixtures hold its results. `icu/oracle.cpp` loads
the pinned `confusables.txt` and fails if ICU's built-in data differs from it.
ICU is built with three small patches in `icu/patches/`, each of which brings
it in line with the current text of UTS #39 or fixes a bug that Unicode 18 data
exposes:

- `0001-hntl.patch`: revision 34 adds Hntl (Traditional Han with Latin) to the
  augmented script sets of Han and Latin characters. ICU 79 knows the script
  code but its spoof checker does not apply the rule.
- `0002-bidi-skeleton-mirroring-buffer.patch`: in Unicode 18, U+221D mirrors
  to U+1DB10, outside the BMP, and ICU's bidiSkeleton overflows its buffer.
- `0003-invisible-enclosing-marks.patch`: revision 34 says a nonspacing mark
  is gc=Mn or gc=Me; ICU's repeated-mark check only looks at gc=Mn.

Drop a patch once ICU ships the change; the fixtures must not change when you do.

**unicode-security** (independent check). The Rust crate behind rustc's
confusable lints, with its tables and those of unicode-script and
unicode-normalization regenerated for Unicode 18 by `rust_regen.py`.
`agreement.py` compares it with ICU. Every difference must fall under a named
rule tied to a point of the spec, or generation fails; `agreement.txt` in the
fixtures records the counts.

## The corpus

`corpus.py` builds about 4,000 strings and 2,000 pairs from a fixed seed: the
curated attacks in `tests/conformance/attacks.py` first, then generated
strings that cover every Recommended script, Latin with each other script,
CJK writing systems, look-alike swaps, invisible and bidirectional controls,
combining marks in every order, emoji sequences, digits from many systems and
arbitrary code points. To add an attack, add an entry to `attacks.py` and
regenerate; `test_fixtures.py` checks that entries marked `confusable_with`
really are confusable.

## Moving to a new Unicode version

1. Update `UNICODE_VERSION` and the hashes in `tools/unicode_sources.py`.
2. Move `icu/build.sh` to an ICU release that implements that version, and
   drop any patch upstream has absorbed.
3. Regenerate. Review the diff of `agreement.txt` and the fixtures, and read
   the Modifications section of the new UTS #39 revision for rules the oracles
   do not implement yet.
