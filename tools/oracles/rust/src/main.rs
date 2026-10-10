//! Rust oracle for the confusable conformance fixtures.
//!
//! Wraps unicode-security (used by rustc's confusable lints) with tables that
//! tools/oracles/rust_regen.py regenerated for the pinned Unicode version.
//! Inputs and outputs are code point sequences written as space-separated hex.
//! generate.py drives this program; see tools/oracles/README.md.
//!
//! Usage:
//!   confusable-oracle info
//!   confusable-oracle skeleton-codepoints
//!   confusable-oracle nfd-codepoints
//!   confusable-oracle properties
//!   confusable-oracle strings INPUT

use std::env;
use std::fs;
use std::io::{self, BufWriter, Write};
use std::process::ExitCode;

use unicode_normalization::UnicodeNormalization;
use unicode_script::UnicodeScript;
use unicode_security::mixed_script::AugmentedScriptSet;
use unicode_security::{
    skeleton, GeneralSecurityProfile, MixedScript, RestrictionLevel, RestrictionLevelDetection,
};

type Out = BufWriter<io::StdoutLock<'static>>;

fn hex(c: char) -> String {
    format!("{:04X}", c as u32)
}

fn hex_seq(chars: impl IntoIterator<Item = char>) -> String {
    chars.into_iter().map(hex).collect::<Vec<_>>().join(" ")
}

fn parse_seq(field: &str) -> String {
    field
        .split_whitespace()
        .map(|token| {
            let value = u32::from_str_radix(token, 16).expect("hex code point");
            char::from_u32(value).expect("Unicode scalar value")
        })
        .collect()
}

fn version((major, minor, patch): (u64, u64, u64)) -> String {
    format!("{major}.{minor}.{patch}")
}

fn all_chars() -> impl Iterator<Item = char> {
    (0..=0x10FFFF).filter_map(char::from_u32)
}

fn level_name(level: RestrictionLevel) -> &'static str {
    match level {
        RestrictionLevel::ASCIIOnly => "ASCII_ONLY",
        RestrictionLevel::SingleScript => "SINGLE_SCRIPT",
        RestrictionLevel::HighlyRestrictive => "HIGHLY_RESTRICTIVE",
        RestrictionLevel::ModeratelyRestrictive => "MODERATELY_RESTRICTIVE",
        RestrictionLevel::MinimallyRestrictive => "MINIMALLY_RESTRICTIVE",
        RestrictionLevel::Unrestricted => "UNRESTRICTED",
    }
}

/// A resolved script set as sorted ISO 15924 codes, "ALL" for the set of all
/// scripts, or "" for the empty set.
fn script_set_name(set: AugmentedScriptSet) -> String {
    if set.is_all() {
        return "ALL".to_string();
    }
    let mut names: Vec<&str> = set.base.iter().map(|s| s.short_name()).collect();
    if set.hanb {
        names.push("Hanb");
    }
    if set.jpan {
        names.push("Jpan");
    }
    if set.kore {
        names.push("Kore");
    }
    names.sort_unstable();
    names.dedup();
    names.join(" ")
}

/// Script_Extensions as sorted ISO 15924 codes, or "" where it is just {Script}.
fn script_extensions(c: char) -> String {
    let extension = c.script_extension();
    if extension.is_common() || extension.is_inherited() {
        return String::new();
    }
    let mut names: Vec<&str> = extension.iter().map(|s| s.short_name()).collect();
    names.sort_unstable();
    if names == [c.script().short_name()] {
        return String::new();
    }
    names.join(" ")
}

/// Writes one property as UCD-style ranges, omitting the default value.
fn dump_property(out: &mut Out, name: &str, default: &str, value_of: impl Fn(u32) -> String) {
    writeln!(out, "## {name}\tdefault={default}").unwrap();
    let mut start = 0u32;
    let mut current = value_of(0);
    for cp in 1..=0x110000u32 {
        let value = if cp <= 0x10FFFF { value_of(cp) } else { "\u{1}".to_string() };
        if value != current {
            if current != default {
                let end = cp - 1;
                if end == start {
                    writeln!(out, "{start:04X}\t{current}").unwrap();
                } else {
                    writeln!(out, "{start:04X}..{end:04X}\t{current}").unwrap();
                }
            }
            start = cp;
            current = value;
        }
    }
}

/// Property values for scalar values; surrogates get the defaults, matching
/// what the UCD files say about them.
fn for_scalar(cp: u32, default: &str, f: impl Fn(char) -> String) -> String {
    char::from_u32(cp).map_or_else(|| default.to_string(), f)
}

fn info(out: &mut Out) {
    writeln!(out, "unicode-security\t{}", version(unicode_security::UNICODE_VERSION)).unwrap();
    writeln!(out, "unicode-script\t{}", version(unicode_script::UNICODE_VERSION)).unwrap();
    let (major, minor, patch) = unicode_normalization::UNICODE_VERSION;
    writeln!(out, "unicode-normalization\t{major}.{minor}.{patch}").unwrap();
}

fn skeleton_codepoints(out: &mut Out) {
    for c in all_chars() {
        let input = c.to_string();
        let result: String = skeleton(&input).collect();
        if result != input {
            writeln!(out, "{}\t{}", hex(c), hex_seq(result.chars())).unwrap();
        }
    }
}

fn nfd_codepoints(out: &mut Out) {
    for c in all_chars() {
        let result: String = c.to_string().nfd().collect();
        if result.chars().ne(std::iter::once(c)) {
            writeln!(out, "{}\t{}", hex(c), hex_seq(result.chars())).unwrap();
        }
    }
}

fn properties(out: &mut Out) {
    dump_property(out, "Script", "Zzzz", |cp| {
        for_scalar(cp, "Zzzz", |c| c.script().short_name().to_string())
    });
    dump_property(out, "Script_Extensions", "", |cp| for_scalar(cp, "", script_extensions));
    dump_property(out, "Identifier_Status", "Restricted", |cp| {
        for_scalar(cp, "Restricted", |c| {
            if c.identifier_allowed() { "Allowed" } else { "Restricted" }.to_string()
        })
    });
    // unicode-security keeps only the first type listed in IdentifierType.txt.
    dump_property(out, "Identifier_Type_First", "Not_Character", |cp| {
        for_scalar(cp, "Not_Character", |c| match c.identifier_type() {
            Some(t) => format!("{t:?}"),
            None => "Not_Character".to_string(),
        })
    });
}

fn strings(out: &mut Out, input: &str) {
    let text = fs::read_to_string(input).expect("readable input");
    for line in text.lines().filter(|line| !line.starts_with('#')) {
        let s = parse_seq(line);
        let skel = hex_seq(skeleton(&s));
        let nfd = hex_seq(s.nfd());
        let level = level_name(s.as_str().detect_restriction_level());
        let resolved = script_set_name(s.as_str().resolve_script_set());
        writeln!(out, "{skel}\t{nfd}\t{level}\t{resolved}").unwrap();
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    let mut out = BufWriter::new(io::stdout().lock());
    match args.iter().skip(1).map(String::as_str).collect::<Vec<_>>().as_slice() {
        ["info"] => info(&mut out),
        ["skeleton-codepoints"] => skeleton_codepoints(&mut out),
        ["nfd-codepoints"] => nfd_codepoints(&mut out),
        ["properties"] => properties(&mut out),
        ["strings", input] => strings(&mut out, input),
        _ => {
            eprintln!(
                "usage: confusable-oracle info | skeleton-codepoints | nfd-codepoints | \
                 properties | strings INPUT"
            );
            return ExitCode::from(64);
        }
    }
    out.flush().unwrap();
    ExitCode::SUCCESS
}
