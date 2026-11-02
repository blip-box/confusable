"""tools/guild_oracle_check.py: the fixtures answer a bug report's reproducer."""

import json
from pathlib import Path

import pytest

from tests.conformance import adapter
from tools import guild_oracle_check as check

# A bug form submission, as guildkit's snapshot shows it: plain text, every
# character outside printable ASCII as U+XXXX.
PAYPAL = "U+0070 U+0430 U+0079 U+0070 U+0430 U+006C"


def body(code_points: str = PAYPAL, function: str = "skeleton(text)") -> str:
    return (
        "Summary\n\nThe skeleton is wrong.\n\n"
        f"Code points\n\n{code_points}\n\n"
        f"Function called\n\n{function}\n\n"
        "Expected result\n\n'paypa1'\n\n"
        "Actual result\n\n'paypal'\n\n"
        "Library version\n\n0.1.0.dev0\n\n"
        "Specification clause\n\nUTS #39 section 4\n"
    )


def test_fields_are_read_by_label() -> None:
    form = check.fields(body())
    assert form["Code points"] == PAYPAL
    assert form["Function called"] == "skeleton(text)"
    assert form["Expected result"] == "'paypa1'"
    assert form["Specification clause"] == "UTS #39 section 4"


def test_decode_and_other_argument() -> None:
    assert check.decode(PAYPAL) == "p" + chr(0x430) + "yp" + chr(0x430) + "l"
    assert check.other_argument('text, "paypal"') == "paypal"
    assert check.other_argument("text, U+0070 U+0061, direction=None") == "pa"
    assert check.other_argument("text") is None


def test_corpus_string_the_library_agrees_on_is_disagrees() -> None:
    assert check.verdict(body()) == "disagrees"
    assert (
        check.verdict(body(function='skeleton(text, direction="rtl")')) == "disagrees"
    )
    assert check.verdict(body(function="restriction_level(text)")) == "disagrees"
    assert check.verdict(body(function="is_mixed_script(text)")) == "disagrees"


def test_pair_from_the_fixtures() -> None:
    assert check.verdict(body(function='match(text, "paypal")')) == "disagrees"
    assert (
        check.verdict(
            body(function="match(text, U+0070 U+0061 U+0079 U+0070 U+0061 U+006C)")
        )
        == "disagrees"
    )
    assert check.verdict(body(function="match(text)")) == "not_run"


def test_single_code_point_properties() -> None:
    assert check.verdict(body("U+0430", "identifier_status(text)")) == "disagrees"
    assert check.verdict(body("U+0430", "identifier_types(text)")) == "disagrees"
    assert check.verdict(body("U+005F", "isxidstart(text)")) == "disagrees"
    assert check.verdict(body("U+0130", "skeleton(text)")) == "disagrees"


def test_input_outside_the_fixtures_is_not_run() -> None:
    text = (
        "U+0071 U+0077 U+0065 U+0072 U+0074 U+0079 U+0075 U+0069 U+006F U+0070 U+0430"
    )
    assert check.decode(text) not in check.string_cases()
    assert check.verdict(body(text)) == "not_run"
    assert check.verdict(body(function="find_invisible(text)")) == "not_run"
    assert (
        check.verdict(body(function="is_allowed(text, joining_controls=True)"))
        == "not_run"
    )
    assert check.verdict(body(function="frobnicate(text)")) == "not_run"


def test_no_reproducer_is_not_applicable() -> None:
    assert check.verdict("Summary\n\nIt is broken.\n") == "not_applicable"
    assert check.verdict(body(code_points="none")) == "not_applicable"
    assert check.verdict(body(function="skeleton")) == "not_applicable"


def test_library_differing_from_the_oracle_confirms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "skeleton", lambda text: "wrong")
    lines: list[str] = []
    assert check.verdict(body(), lines.append) == "confirms"
    assert lines[-1] == "oracle: paypal; library: wrong"
    assert all(line.isascii() for line in lines)


def test_main_writes_the_verdict(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"body": body()}), encoding="ascii")
    out = tmp_path / "oracle.txt"
    assert check.main(["--snapshot", str(snapshot), "--out", str(out)]) == 0
    assert out.read_text(encoding="ascii") == "disagrees\n"


def test_main_reports_error_on_a_bad_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("{not json", encoding="ascii")
    out = tmp_path / "oracle.txt"
    assert check.main(["--snapshot", str(snapshot), "--out", str(out)]) == 0
    assert out.read_text(encoding="ascii") == "error\n"
