"""Pinned Unicode source files for the oracles and the data generator.

Each file is downloaded once into a local cache and checked against a SHA-256
pin and its version header before use, so a changed or truncated download fails
loudly instead of quietly producing different fixtures or tables.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

UNICODE_VERSION = "18.0.0"
BASE_URL = f"https://www.unicode.org/Public/{UNICODE_VERSION}/"
CACHE_DIR = (
    Path(os.environ.get("CONFUSABLE_UNICODE_CACHE", Path(__file__).parent / ".cache"))
    / "unicode"
    / UNICODE_VERSION
)


@dataclass(frozen=True)
class Source:
    """A file under BASE_URL, its pinned hash, and the line naming its version."""

    path: str
    sha256: str
    # None for files without a version header (UnicodeData.txt); the hash
    # alone pins those.
    version_line: str | None


def _ucd(name: str, sha256: str) -> Source:
    stem = name.rsplit("/", 1)[-1].removesuffix(".txt")
    return Source(f"ucd/{name}", sha256, f"# {stem}-{UNICODE_VERSION}.txt")


def _versioned(path: str, sha256: str, version: str = UNICODE_VERSION) -> Source:
    return Source(path, sha256, f"# Version: {version}")


SOURCES: dict[str, Source] = {
    source.path: source
    for source in (
        # UTS #39 data.
        _versioned(
            "security/confusables.txt",
            "6ed3ee967c9dfdf6677d563c9985182fbc50a2efb7d6059cd57b2e2ce18f5b92",
        ),
        _versioned(
            "security/confusablesSummary.txt",
            "653036722c0d31e06054d71e80a0a6c30766c8f763fd4e458d7fc740d25104ab",
        ),
        _versioned(
            "security/IdentifierStatus.txt",
            "5863c7d99ca18f213c41c7318aa5528bebfb6d32ec0f1d5944e37192c119aebd",
        ),
        _versioned(
            "security/IdentifierType.txt",
            "fa24851acc669e58670e354e7b98a4ec8f52a809ec4f80524b6a60efdb868831",
        ),
        _versioned(
            "security/intentional.txt",
            "5b69cdfd7be6be45d51b9cf7ec799df91c1acc47c557d66c92a8d6623df78b0e",
        ),
        # Unicode Character Database.
        _ucd(
            "DerivedCoreProperties.txt",
            "09c928886a178fcafd93c29e4bd59073a058e5a100b716d425cb563ab50f68c9",
        ),
        _ucd(
            "DerivedNormalizationProps.txt",
            "98ac7f67d985fe781e317f6182e885e94cabb0c314769e6dd73e48b226931ccd",
        ),
        _ucd(
            "NormalizationTest.txt",
            "25a50d816764b04abfb4a646d3eb2b2a803284c3873d9a06757b94fe4513dde3",
        ),
        _ucd(
            "PropList.txt",
            "f438f532e8737bb8a2702126cdf9c4af5e357c58c7acf9d9eb2fc7c1a1d955d6",
        ),
        _ucd(
            "PropertyValueAliases.txt",
            "06c4c8eaf7b0bf34abe73b113da1215bd784ac254d4c223600b90267caa4bbbd",
        ),
        _ucd(
            "ScriptExtensions.txt",
            "5c9d34a922f687726f2a8bcf57d49f905987e51f1b21b58c95a00fbe255cec23",
        ),
        _ucd(
            "Scripts.txt",
            "0071fd81b6aeae25f6e8bce8efec3066a6476a91b49bdb2f52dc76e817862a6a",
        ),
        _ucd(
            "StandardizedVariants.txt",
            "c7ae634a7e2bb0932258548a1e81df984fbb38e30cecf4269391d6a4f94581ac",
        ),
        Source(
            "ucd/UnicodeData.txt",
            "0736451de439ae7baf1425136617da495e09ee5afbe6e394374db7009ea08950",
            None,
        ),
        _ucd(
            "auxiliary/GraphemeBreakProperty.txt",
            "0839dcb79e4ac639ecd538b1abf7c9d22e3f9dd265b7e182d33627aa4d75b45a",
        ),
        _ucd(
            "auxiliary/GraphemeBreakTest.txt",
            "b0cf047ee94485bbdc846de2b902f5f8a815f6b674f9d04223cddadd91c9df31",
        ),
        _versioned(
            "ucd/emoji/emoji-data.txt",
            "80d00f8e616a0ef27fd6b8de3b758c06383b5d917e2977709578e68baf733bf1",
        ),
        # Emoji sequences carry a two-part version.
        _versioned(
            "emoji/emoji-sequences.txt",
            "1823dce71f3dd9cb0ad1976797baee4ffbdc1909756f43af8ce4c57f732843a4",
            "18.0",
        ),
        _versioned(
            "emoji/emoji-zwj-sequences.txt",
            "f61b5213bdf85a57741a9f903cb38d0f39a3d13be6ff4aca3b39857e859a9191",
            "18.0",
        ),
    )
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(path: str) -> Path:
    """Return the local path of a pinned source file, downloading it if needed."""
    source = SOURCES[path]
    target = CACHE_DIR / path
    if not target.exists() or _sha256(target) != source.sha256:
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE_URL + path, timeout=120) as response:
            data = response.read()
        partial = target.with_name(target.name + ".part")
        partial.write_bytes(data)
        partial.replace(target)
    actual = _sha256(target)
    if actual != source.sha256:
        raise RuntimeError(f"{path}: expected sha256 {source.sha256}, got {actual}")
    if source.version_line is not None:
        with target.open(encoding="utf-8-sig") as lines:
            header = [next(lines, "").rstrip("\n") for _ in range(50)]
        if source.version_line not in header:
            raise RuntimeError(f"{path}: no {source.version_line!r} line in its header")
    return target


def fetch_all() -> dict[str, Path]:
    """Fetch every pinned source and map its path to the local file."""
    return {path: fetch(path) for path in SOURCES}


if __name__ == "__main__":
    for path, local in fetch_all().items():
        print(f"{path}\t{local}")
