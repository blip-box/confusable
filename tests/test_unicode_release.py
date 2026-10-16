import subprocess
from pathlib import Path

import pytest

from tools import unicode_release
from tools.unicode_sources import SOURCES, UNICODE_VERSION

README = """This directory contains final data files for version 19.0.0 of the
Unicode Character Database.
"""


def test_reads_the_final_version_from_the_ucd_readme() -> None:
    assert unicode_release.latest_version(README) == "19.0.0"


def test_rejects_a_readme_without_a_final_version() -> None:
    with pytest.raises(ValueError, match="final version"):
        unicode_release.latest_version("This directory contains draft data files.")


@pytest.mark.parametrize("version", ["17.0.0", UNICODE_VERSION, "19"])
def test_prepare_only_moves_forward(version: str) -> None:
    with pytest.raises(SystemExit):
        unicode_release.prepare(version)


def test_prepare_repins_every_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "unicode_sources.py"
    manifest.write_text(unicode_release.MANIFEST.read_text(encoding="utf-8"))
    monkeypatch.setattr(unicode_release, "MANIFEST", manifest)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)

    def download(url: str) -> bytes:
        # A distinct file per URL, with the header a 19.0.0 release would carry.
        path = url.split("/19.0.0/", 1)[1]
        line = SOURCES[path].version_line or ""
        line = line.replace("18.0.0", "19.0.0").replace("18.0", "19.0")
        return f"{line}\n{path}\n".encode()

    monkeypatch.setattr(unicode_release, "_download", download)
    unicode_release.prepare("19.0.0")

    text = manifest.read_text(encoding="utf-8")
    assert 'UNICODE_VERSION = "19.0.0"' in text
    for source in SOURCES.values():
        assert source.sha256 not in text
