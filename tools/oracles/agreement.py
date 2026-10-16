"""Cross-check the ICU oracle against the Rust oracle.

ICU is the primary oracle. unicode-security is an independent implementation
of the same specification, so the two should agree. Where they do not, the
difference must be explained by one of RULES, each naming the point of UTS #39
where unicode-security departs from the current text. Any other difference is
a bug in an oracle or in this harness, and generation stops.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

RULES = {
    "rust-keeps-default-ignorables": (
        "UTS #39 internalSkeleton removes Default_Ignorable_Code_Point "
        "characters (step 2). unicode-security 0.1.2 predates that step and "
        "keeps them, so its skeleton differs wherever one occurs."
    ),
    "rust-lacks-hntl": (
        "UTS #39 revision 34 adds Hntl to the augmented script sets of Han and "
        "Latin characters. unicode-security 0.1.2 predates it, so its resolved "
        "script sets lack Hntl, and strings that are single-script only through "
        "Hntl (Latin with Han) get a lower restriction level."
    ),
    "rust-unknown-is-empty": (
        "Unassigned and private-use code points have Script_Extensions {Zzzz} "
        "(Unknown), so by UTS #39 section 5.1 a string made only of them has "
        "the resolved script set {Zzzz}, as ICU computes. unicode-script "
        "represents Unknown as the empty set instead."
    ),
}


@dataclass
class Check:
    """Counts for one comparison between the oracles."""

    name: str
    compared: int = 0
    identical: int = 0
    explained: Counter[str] = field(default_factory=Counter)


@dataclass
class Report:
    checks: dict[str, Check] = field(default_factory=dict)
    examples: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    unexplained: list[str] = field(default_factory=list)

    def check(self, name: str) -> Check:
        return self.checks.setdefault(name, Check(name))

    def same(self, check: str) -> None:
        c = self.check(check)
        c.compared += 1
        c.identical += 1

    def explain(self, check: str, rule: str, example: str) -> None:
        assert rule in RULES
        c = self.check(check)
        c.compared += 1
        c.explained[rule] += 1
        if len(self.examples[rule]) < 3:
            self.examples[rule].append(f"{check}: {example}")

    def fail(self, check: str, example: str) -> None:
        self.check(check).compared += 1
        self.unexplained.append(f"{check}: {example}")


def _codepoint_map(text: str) -> dict[int, str]:
    out = {}
    for line in text.splitlines():
        cp, value = line.split("\t")
        out[int(cp, 16)] = value
    return out


def _properties(text: str) -> dict[str, dict[int, str]]:
    """Property name -> {code point: value} for the non-default entries."""
    out: dict[str, dict[int, str]] = {}
    current: dict[int, str] = {}
    for line in text.splitlines():
        if line.startswith("## "):
            current = out.setdefault(line[3:].split("\t")[0], {})
            continue
        span, value = line.split("\t")
        start, _, end = span.partition("..")
        for cp in range(int(start, 16), int(end or start, 16) + 1):
            current[cp] = value
    return out


def _strip(rss: str, script: str) -> str:
    return " ".join(s for s in rss.split() if s != script)


def cross_check(strings: list[str], icu: dict[str, str], rust: dict[str, str]) -> str:
    report = Report()
    icu_props = _properties(icu["properties"])
    rust_props = _properties(rust["properties"])
    ignorable = set(icu_props["Default_Ignorable_Code_Point"])

    # NFD of every code point must match exactly.
    icu_nfd, rust_nfd = _codepoint_map(icu["nfd"]), _codepoint_map(rust["nfd"])
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        if icu_nfd.get(cp) == rust_nfd.get(cp):
            report.same("code point NFD")
        else:
            report.fail("code point NFD", f"U+{cp:04X}")

    # Skeleton of every code point.
    icu_skel, rust_skel = (
        _codepoint_map(icu["skeleton"]),
        _codepoint_map(rust["skeleton"]),
    )
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        a, b = icu_skel.get(cp), rust_skel.get(cp)
        if a == b:
            report.same("code point skeleton")
        elif cp in ignorable and a == "":
            report.explain(
                "code point skeleton",
                "rust-keeps-default-ignorables",
                f"U+{cp:04X} icu=<empty> rust={b or 'itself'}",
            )
        else:
            report.fail("code point skeleton", f"U+{cp:04X} icu={a} rust={b}")

    # Properties both oracles expose.
    for name in ("Script", "Script_Extensions", "Identifier_Status"):
        a_map, b_map = icu_props[name], rust_props[name]
        for cp in set(a_map) | set(b_map):
            if a_map.get(cp) == b_map.get(cp):
                report.same(f"{name} (non-default entries)")
            else:
                report.fail(
                    name, f"U+{cp:04X} icu={a_map.get(cp)} rust={b_map.get(cp)}"
                )
    # unicode-security keeps only the first type listed in IdentifierType.txt.
    icu_types, rust_first = (
        icu_props["Identifier_Type"],
        rust_props["Identifier_Type_First"],
    )
    for cp in set(icu_types) | set(rust_first):
        types = icu_types.get(cp, "Not_Character").split()
        if rust_first.get(cp, "Not_Character") in types:
            report.same("Identifier_Type (non-default entries)")
        else:
            report.fail(
                "Identifier_Type", f"U+{cp:04X} icu={types} rust={rust_first.get(cp)}"
            )

    # Per-string results.
    icu_rows = [line.split("\t") for line in icu["strings"].splitlines()]
    rust_rows = [line.split("\t") for line in rust["strings"].splitlines()]
    for text, icu_row, rust_row in zip(strings, icu_rows, rust_rows, strict=True):
        _, internal, _, nfd, rss, level, *_ = icu_row
        r_skeleton, r_nfd, r_level, r_rss = rust_row
        label = " ".join(f"{ord(c):04X}" for c in text) or "<empty>"
        has_ignorable = any(ord(c) in ignorable for c in text)

        if nfd == r_nfd:
            report.same("string NFD")
        else:
            report.fail("string NFD", label)

        if internal == r_skeleton:
            report.same("string internalSkeleton")
        elif has_ignorable:
            report.explain(
                "string internalSkeleton", "rust-keeps-default-ignorables", label
            )
        else:
            report.fail(
                "string internalSkeleton", f"{label} icu={internal} rust={r_skeleton}"
            )

        # Hntl is only ever added, so removing it from ICU's set must give
        # exactly unicode-security's set.
        if rss == r_rss:
            report.same("resolved script set")
        elif rss != "ALL" and _strip(rss, "Hntl") == r_rss:
            report.explain(
                "resolved script set", "rust-lacks-hntl", f"{label} icu={rss}"
            )
        elif rss == "Zzzz" and r_rss == "":
            report.explain("resolved script set", "rust-unknown-is-empty", label)
        else:
            report.fail("resolved script set", f"{label} icu={rss} rust={r_rss}")

        if level == r_level:
            report.same("restriction level")
        elif level == "SINGLE_SCRIPT" and rss != "ALL" and _strip(rss, "Hntl") == "":
            report.explain(
                "restriction level",
                "rust-lacks-hntl",
                f"{label} icu={level} rust={r_level}",
            )
        else:
            report.fail(
                "restriction level", f"{label} icu={level} rust={r_level} rss={rss}"
            )

    if report.unexplained:
        shown = "\n".join(report.unexplained[:40])
        raise SystemExit(
            f"{len(report.unexplained)} unexplained differences between ICU and "
            f"unicode-security:\n{shown}"
        )
    return render(report)


def render(report: Report) -> str:
    lines = [
        "# agreement.txt: ICU against unicode-security (the Rust oracle).",
        "# Generated by tools/oracles/generate.py. Do not edit by hand.",
        "#",
        "# ICU is the primary oracle and supplies the other fixtures. unicode-security",
        "# is an independent implementation; every difference between the two falls",
        "# under one of the rules below, and generation fails on any other.",
        "#",
        "# Column 1: check. Column 2: cases compared. Column 3: identical.",
        "# Column 4: differences, by rule.",
    ]
    for check in report.checks.values():
        explained = " ".join(
            f"{rule}={n}" for rule, n in sorted(check.explained.items())
        )
        lines.append(f"{check.name}\t{check.compared}\t{check.identical}\t{explained}")
    lines.append("#")
    lines.append("# Rules, with up to three examples each:")
    for rule, text in RULES.items():
        lines.append(f"# {rule}: {text}")
        lines.extend(f"#   {example}" for example in report.examples[rule])
    return "\n".join(lines) + "\n"
