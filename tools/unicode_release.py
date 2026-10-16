"""Notice new Unicode releases, and prepare the move to one.

    python -m tools.unicode_release check
    python -m tools.unicode_release issue VERSION
    python -m tools.unicode_release prepare VERSION

check compares the latest final release of the Unicode Character Database with
the pinned version, and in GitHub Actions writes the result to $GITHUB_OUTPUT.
issue prints the body of the issue that tracks the move to a new version.
prepare re-pins every source file in tools/unicode_sources.py by its hash at
the new version, after checking each file's version header, and regenerates
the package's tables. The conformance fixtures cannot follow automatically:
they need an ICU release that implements the new version.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from tools.unicode_sources import EMOJI_VERSION, SOURCES, UNICODE_VERSION

MANIFEST = Path(__file__).with_name("unicode_sources.py")
LATEST_README = "https://www.unicode.org/Public/UCD/latest/ucd/ReadMe.txt"
VERSION = re.compile(r"\d+\.\d+\.\d+")


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "confusable-release-check"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data: bytes = response.read()
    return data


def latest_version(readme: str) -> str:
    """Return the version a UCD ReadMe.txt says it holds final data for."""
    match = re.search(r"final data files for version (\d+\.\d+\.\d+)", readme)
    if match is None:
        raise ValueError("the UCD ReadMe.txt no longer names a final version")
    return match.group(1)


def check() -> None:
    latest = latest_version(_download(LATEST_README).decode("utf-8"))
    newer = _key(latest) > _key(UNICODE_VERSION)
    print(f"pinned Unicode {UNICODE_VERSION}; latest final release {latest}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as out:
            out.write(f"latest={latest}\nnewer={'true' if newer else 'false'}\n")


def issue(version: str) -> None:
    print(
        f"""Unicode {version} is out; confusable pins {UNICODE_VERSION}.

Moving to it takes a person, because the specifications can change their
algorithms and the conformance oracles need an ICU release for the new version.

- [ ] Read the Modifications sections of the new revisions of UTS #39, UAX #9,
      UAX #29 and UAX #31, and note every change to an algorithm we implement.
- [ ] On a branch, run `uv run python -m tools.unicode_release prepare {version}`.
      It re-pins every Unicode source by hash and regenerates the tables.
- [ ] Move `tools/oracles/icu/build.sh` to an ICU release that implements
      Unicode {version}, drop the patches it absorbed, and regenerate the Rust
      oracle's crates (`tools/oracles/rust_regen.py`).
- [ ] Regenerate the fixtures (`python -m tools.oracles.generate`) and review the
      diff, `agreement.txt` above all.
- [ ] Update the versions and spec revisions in `AGENTS.md`.

Opened by the Unicode release workflow (`.github/workflows/unicode-release.yml`).
"""
    )


def prepare(version: str) -> None:
    if not VERSION.fullmatch(version) or _key(version) <= _key(UNICODE_VERSION):
        raise SystemExit(f"{version} is not a version newer than {UNICODE_VERSION}")
    emoji_version = version.rsplit(".", 1)[0]
    text = MANIFEST.read_text(encoding="utf-8")
    text = text.replace(
        f'UNICODE_VERSION = "{UNICODE_VERSION}"', f'UNICODE_VERSION = "{version}"'
    )
    for path, source in SOURCES.items():
        data = _download(f"https://www.unicode.org/Public/{version}/{path}")
        if source.version_line is not None:
            expected = source.version_line.replace(UNICODE_VERSION, version).replace(
                EMOJI_VERSION, emoji_version
            )
            header = data.decode("utf-8-sig").splitlines()[:50]
            if expected not in header:
                raise SystemExit(f"{path}: no {expected!r} line in its header")
        text = text.replace(source.sha256, hashlib.sha256(data).hexdigest())
        print(f"re-pinned {path}")
    MANIFEST.write_text(text, encoding="utf-8")
    # A fresh interpreter, so the generator imports the new manifest.
    subprocess.run([sys.executable, "-m", "tools.generate_tables"], check=True)
    print("Next: the ICU and Rust oracles, then the fixtures; see the release issue.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    for name in ("issue", "prepare"):
        commands.add_parser(name).add_argument("version")
    args = parser.parse_args()
    if args.command == "check":
        check()
    elif not VERSION.fullmatch(args.version):
        raise SystemExit(f"not a Unicode version: {args.version!r}")
    elif args.command == "issue":
        issue(args.version)
    else:
        prepare(args.version)


if __name__ == "__main__":
    main()
