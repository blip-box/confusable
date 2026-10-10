"""Regenerate the Rust oracle's crates for the pinned Unicode version.

unicode-security, unicode-script and unicode-normalization each generate their
tables with scripts/unicode.py from one version constant, but their published
releases lag Unicode. This module downloads each pinned release, checks it
against the crates.io checksum, points its generator at the pinned Unicode
version, and runs the generator on the pinned local Unicode files with network
access blocked. The patched crates land in rust/vendor/, where
rust/Cargo.toml's [patch.crates-io] picks them up.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from tools.unicode_sources import UNICODE_VERSION, fetch_all

VENDOR = Path(__file__).resolve().parent / "rust" / "vendor"


@dataclass(frozen=True)
class Crate:
    """A pinned crate release and the edits that retarget its generator."""

    name: str
    version: str
    sha256: str  # the "cksum" from the crates.io index
    # (pattern, replacement) pairs applied to scripts/unicode.py. Each pattern
    # must match exactly once, so a changed generator fails loudly.
    edits: tuple[tuple[str, str], ...]


MAJOR, MINOR, PATCH = UNICODE_VERSION.split(".")
TUPLE_VERSION = (
    r"UNICODE_VERSION = \(\d+, \d+, \d+\)",
    f"UNICODE_VERSION = ({MAJOR}, {MINOR}, {PATCH})",
)

CRATES = (
    Crate(
        "unicode-security",
        "0.1.2",
        "2e4ddba1535dd35ed8b61c52166b7155d7f4e4b8847cec6f48e71dc66d8b5e50",
        (TUPLE_VERSION,),
    ),
    Crate(
        "unicode-script",
        "0.5.8",
        "383ad40bb927465ec0ce7720e033cb4ca06912855fc35db31b5755d0de75b1ee",
        (TUPLE_VERSION,),
    ),
    Crate(
        "unicode-normalization",
        "0.1.25",
        "5fd4f6878c9cb28d874b009da9e8d183b5abc80117c40bbd187a1fde336be6e8",
        (
            (r'UNICODE_VERSION = "[\d.]+"', f'UNICODE_VERSION = "{UNICODE_VERSION}"'),
            # This generator downloads with urllib; read the pinned files instead.
            (
                r"resp = urllib\.request\.urlopen\(UCD_URL \+ filename\)\n"
                r"(\s+)return resp\.read\(\)\.decode\('utf-8'\)",
                r"with open(filename, encoding='utf-8') as f:\n\1    return f.read()",
            ),
        ),
    ),
)

# A curl that always fails, so a generator that wants a file we did not pin
# stops instead of downloading something unpinned.
FAKE_CURL = '#!/bin/sh\necho "rust_regen: refusing to download $*" >&2\nexit 1\n'


def download(crate: Crate) -> bytes:
    url = (
        f"https://static.crates.io/crates/{crate.name}/"
        f"{crate.name}-{crate.version}.crate"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "confusable-oracles"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data: bytes = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != crate.sha256:
        raise RuntimeError(
            f"{crate.name}: expected sha256 {crate.sha256}, got {actual}"
        )
    return data


def retarget(generator: Path, crate: Crate) -> None:
    text = generator.read_text(encoding="utf-8")
    for pattern, replacement in crate.edits:
        text, count = re.subn(pattern, replacement, text)
        if count != 1:
            raise RuntimeError(f"{crate.name}: {pattern!r} matched {count} times")
    generator.write_text(text, encoding="utf-8")


def regenerate(crate: Crate, sources: dict[str, Path]) -> None:
    target = VENDOR / crate.name
    shutil.rmtree(target, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(download(crate)), mode="r:gz") as archive:
        archive.extractall(VENDOR, filter="data")
    (VENDOR / f"{crate.name}-{crate.version}").rename(target)

    generator = target / "scripts" / "unicode.py"
    retarget(generator, crate)
    with tempfile.TemporaryDirectory() as work:
        workdir = Path(work)
        for local in sources.values():
            shutil.copy(local, workdir / local.name)
        bin_dir = workdir / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(FAKE_CURL)
        curl.chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        subprocess.run(
            [sys.executable, str(generator)],
            cwd=workdir,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        shutil.copy(workdir / "tables.rs", target / "src" / "tables.rs")


def main() -> None:
    # Not sys.version_info itself, which mypy would treat as a platform check.
    if tuple(sys.version_info) < (3, 12):
        # unicode-normalization's generator uses itertools.batched.
        raise SystemExit("rust_regen needs Python 3.12 or later")
    sources = fetch_all()
    VENDOR.mkdir(exist_ok=True)
    for crate in CRATES:
        regenerate(crate, sources)
        print(f"regenerated {crate.name} {crate.version} for Unicode {UNICODE_VERSION}")


if __name__ == "__main__":
    main()
