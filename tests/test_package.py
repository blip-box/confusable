import importlib.metadata

import confusable


def test_version_matches_distribution_metadata() -> None:
    assert confusable.__version__ == importlib.metadata.version("confusable")


def test_has_no_runtime_dependencies() -> None:
    requirements = importlib.metadata.requires("confusable") or []
    assert [r for r in requirements if "extra ==" not in r] == []


def test_unicode_version_is_the_pinned_one() -> None:
    from tools.unicode_sources import UNICODE_VERSION

    assert confusable.unicode_version == UNICODE_VERSION
