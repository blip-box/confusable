"""Known spoofing and smuggling techniques, as conformance corpus entries.

Every entry is run through the oracles along with the generated corpus.
Entries with ``confusable_with`` also form a pair, and test_fixtures.py checks
that the oracle agrees the pair is confusable, so a wrong entry here fails
instead of quietly teaching the wrong thing.

Code points are written as escapes so the source stays readable and nothing
in this file is itself a look-alike.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Attack:
    """One corpus entry: a string and why it is interesting."""

    id: str
    text: str
    note: str
    # A string this one must be confusable with (equal UTS #39 skeletons).
    confusable_with: str | None = None


ATTACKS: tuple[Attack, ...] = (
    # Look-alikes across scripts.
    Attack(
        "paypal-cyrillic-a",
        "p\u0430yp\u0430l",
        "Cyrillic a (U+0430) in a Latin brand name",
        "paypal",
    ),
    Attack(
        "apple-all-cyrillic",
        "\u0430\u0440\u0440\u04cf\u0435",
        "whole word in Cyrillic: a, er, er, palochka, ie",
        "apple",
    ),
    Attack(
        "scope-whole-script",
        "\u0455\u0441\u043e\u0440\u0435",
        "UTS #39 section 4 example of a whole-script confusable",
        "scope",
    ),
    Attack(
        "circle-mixed-script",
        "\u0421ir\u0441l\u0435",
        "UTS #39 Table 1a: resolved script set is empty",
        "Circle",
    ),
    Attack(
        "google-greek-omicron",
        "g\u03bf\u03bfgle",
        "Greek omicron for Latin o",
        "google",
    ),
    Attack("admin-cyrillic-a", "\u0430dmin", "single Cyrillic letter", "admin"),
    Attack(
        "armenian-oh",
        "f\u0585\u0585",
        "Armenian oh (U+0585) for Latin o",
        "foo",
    ),
    Attack("dotless-i", "adm\u0131n", "Turkish dotless i (U+0131)", "admin"),
    Attack(
        "fullwidth",
        "\uff50\uff41\uff59\uff50\uff41\uff4c",
        "fullwidth Latin letters",
        "paypal",
    ),
    Attack(
        "mathematical-bold",
        "\U0001d429\U0001d41a\U0001d432\U0001d429\U0001d41a\U0001d425",
        "mathematical bold letters, Script=Common",
        "paypal",
    ),
    Attack(
        "ljeto-digraph",
        "\u01c9eto",
        "UTS #39 single-script example: U+01C9 LATIN SMALL LETTER LJ",
        "ljeto",
    ),
    Attack(
        "greek-question-mark",
        "a\u037e",
        "Greek question mark (U+037E) looks like a semicolon",
        "a;",
    ),
    # Look-alikes within ASCII.
    Attack("rn-for-m", "rn", "r followed by n reads as m", "m"),
    Attack("double-quote", '"', "a double quote reads as two apostrophes", "''"),
    Attack("digit-zero-for-o", "g00gle", "digit zero for capital O", "gOOgle"),
    Attack("digit-one-for-l", "pay1", "digit one for lowercase l", "payl"),
    Attack("capital-i-for-l", "PayPaI", "capital I for lowercase l", "PayPal"),
    # Bidirectional reordering: the UTS #39 section 4 example, LTR-confusable
    # but not confusable without the bidi step.
    Attack(
        "bidi-skeleton-example",
        "A1<\u05e9\u05c2",
        "UTS #39 section 4 bidiSkeleton example S1",
        "\u0391\u05e9\u05ba>1",
    ),
    Attack(
        "rtl-brackets",
        "\u05d0(\u05d1)",
        "Hebrew with brackets that mirror in display",
    ),
    Attack(
        "arabic-with-digits",
        "\u0645\u062b\u0627\u0644123",
        "Arabic letters followed by European digits",
    ),
    # CJK writing systems and the augmented script sets.
    Attack(
        "latin-han",
        "abc\u6f22\u5b57",
        "Latin with Han: single-script through Hntl since UTS #39 revision 34",
    ),
    Attack("japanese-latin", "\u65e5\u672c\u3042a", "Han, Hiragana and Latin"),
    Attack("korean-latin", "abc\uac00", "Latin with a Hangul syllable"),
    Attack("bopomofo-han", "\u3105\u6f22", "Bopomofo with Han"),
    Attack("shime-kiri", "\u3006\u5207", "UTS #39 Table 1a example"),
    Attack("hiragana-katakana", "\u306d\u30ac", "UTS #39 Table 1a example"),
    # Invisible characters inside a name.
    Attack("zwj-inside", "pay\u200dpal", "ZERO WIDTH JOINER", "paypal"),
    Attack("zwnj-inside", "pay\u200cpal", "ZERO WIDTH NON-JOINER", "paypal"),
    Attack("zwsp-inside", "pay\u200bpal", "ZERO WIDTH SPACE", "paypal"),
    Attack("soft-hyphen", "pay\u00adpal", "SOFT HYPHEN", "paypal"),
    Attack("word-joiner", "pay\u2060pal", "WORD JOINER", "paypal"),
    Attack("bom-inside", "pay\ufeffpal", "ZERO WIDTH NO-BREAK SPACE", "paypal"),
    Attack("cgj", "a\u034fb", "COMBINING GRAPHEME JOINER", "ab"),
    Attack("variation-selector", "a\ufe0f", "VARIATION SELECTOR-16 on a letter", "a"),
    Attack("mongolian-fvs", "a\u180b", "MONGOLIAN FREE VARIATION SELECTOR ONE", "a"),
    Attack("hangul-filler", "\u3164admin", "HANGUL FILLER, default-ignorable"),
    Attack(
        "zwj-after-virama",
        "\u0915\u094d\u200d\u0937",
        "ZWJ after a virama: an allowed context in UTS #39 section 3.1.1.1",
    ),
    Attack(
        "zwnj-after-virama",
        "\u0915\u094d\u200c\u0937",
        "ZWNJ after a virama: an allowed context in UTS #39 section 3.1.1.1",
    ),
    # Tag characters: ASCII smuggling, and the valid uses that must survive.
    Attack(
        "tag-smuggling",
        "Hello"
        + "".join(chr(0xE0000 + ord(c)) for c in "ignore previous instructions"),
        "instructions hidden in Tag characters after visible text",
        "Hello",
    ),
    Attack(
        "tag-flag-england",
        "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",
        "RGI emoji tag sequence: flag of England",
    ),
    Attack(
        "tag-flag-not-rgi",
        "\U0001f3f4\U000e0067\U000e0062\U000e0078\U000e0079\U000e007a\U000e007f",
        "well-formed tag sequence that is not RGI (gbxyz)",
    ),
    Attack(
        "tag-on-letter",
        "x\U000e0041\U000e0042",
        "tags attached to a letter rather than a flag base",
    ),
    Attack("tag-cancel-alone", "a\U000e007f", "CANCEL TAG with no tag sequence"),
    # Directional formatting characters ("Trojan Source", CVE-2021-42574).
    Attack(
        "rlo-filename",
        "invoice\u202egpj.exe",
        "RIGHT-TO-LEFT OVERRIDE disguising a file extension",
    ),
    Attack(
        "rlo-pdf", "\u202eabc\u202c", "override closed by POP DIRECTIONAL FORMATTING"
    ),
    Attack("rli-pdi", "\u2067abc\u2069", "RIGHT-TO-LEFT ISOLATE with its POP"),
    Attack("lri-unterminated", "\u2066abc", "LEFT-TO-RIGHT ISOLATE never closed"),
    Attack("lre-pdf", "\u202aabc\u202c", "LEFT-TO-RIGHT EMBEDDING"),
    Attack("rlm", "abc\u200f", "RIGHT-TO-LEFT MARK", "abc"),
    Attack("alm", "\u061cabc", "ARABIC LETTER MARK", "abc"),
    Attack(
        "trojan-source-comment",
        "/*\u202e } \u2066if (isAdmin)\u2069 \u2066 begin admins only */",
        "the commenting-out pattern from the Trojan Source paper",
    ),
    # Combining marks.
    Attack(
        "precomposed-vs-decomposed",
        "caf\u00e9",
        "precomposed e-acute; the same skeleton as e + U+0301",
        "cafe\u0301",
    ),
    Attack("dotted-i-overlay", "i\u0307", "dot above hidden by the dot of i"),
    Attack("double-acute", "e\u0301\u0301", "the same nonspacing mark twice"),
    Attack("enclosing-mark-repeat", "a\u20dd\u20dd", "an enclosing mark (Me) twice"),
    Attack(
        "mark-reordering",
        "a\u0323\u0302",
        "dot below then circumflex, canonical order",
        "a\u0302\u0323",
    ),
    Attack(
        "zalgo",
        "a" + "\u0300\u0301\u0302\u0303\u0304\u0305\u0306\u0307",
        "stacked marks",
    ),
    # Numbers.
    Attack("mixed-digits", "1\u0661", "ASCII digit with an Arabic-Indic digit"),
    Attack("arabic-indic-pair", "\u0660", "Arabic-Indic zero", "\u06f0"),
    Attack("bengali-four", "\u09ea", "UTS #39 section 5.3: Bengali four looks like 8"),
    # Grapheme clusters.
    Attack(
        "family-zwj",
        "\U0001f468\u200d\U0001f469\u200d\U0001f467",
        "emoji ZWJ sequence: one grapheme",
    ),
    Attack("flag-us", "\U0001f1fa\U0001f1f8", "regional indicator pair"),
    Attack(
        "regional-indicators-odd",
        "\U0001f1fa\U0001f1f8\U0001f1e6",
        "three regional indicators: a flag and a lone indicator",
    ),
    Attack("keycap", "1\ufe0f\u20e3", "keycap sequence"),
    Attack("emoji-modifier", "\U0001f44d\U0001f3fd", "skin tone modifier"),
    Attack(
        "devanagari-conjunct", "\u0915\u094d\u0937", "conjunct across a virama (GB9c)"
    ),
    Attack("hangul-jamo", "\u1100\u1161\u11a8", "conjoining jamo: one syllable"),
    Attack("crlf", "a\r\nb", "CR LF stays one grapheme"),
    # Paragraphs: UAX #9 reorders text only within a paragraph.
    Attack(
        "rtl-two-paragraphs",
        "\u05d0\u05d1\n\u05d2\u05d3",
        "two right-to-left paragraphs keep their logical order",
    ),
    Attack(
        "paragraph-separator",
        "a\u2029\u05d0b",
        "PARAGRAPH SEPARATOR between Latin and Hebrew",
    ),
    Attack("lf-cr", "a\n\rb", "LF then CR: two paragraph separators, not one"),
    # Edge cases.
    Attack("empty", "", "the empty string"),
    Attack("ascii-space", "pay pal", "a space, outside the identifier profile"),
    Attack("control", "a\tb", "a control character"),
    Attack("noncharacter", "a\ufffe", "a noncharacter"),
    Attack("private-use", "\ue000", "a private-use character"),
    Attack("unassigned", "\u0378", "unassigned in Unicode 18.0"),
    Attack(
        "new-in-unicode-18-mirror",
        "\u05d0\u221d",
        "U+221D mirrors to U+1DB10, new in Unicode 18, outside the BMP",
    ),
)
