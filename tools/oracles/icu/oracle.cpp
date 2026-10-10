// ICU oracle for the confusable conformance fixtures.
//
// Every input and output string is a sequence of code points written as
// space-separated hex, so the fixtures stay ASCII and unambiguous. generate.py
// drives this program; see tools/oracles/README.md.
//
// UTS #39 defines skeleton(X) as bidiSkeleton(LTR, X); ICU calls the bidi-free
// part internalSkeleton "getSkeleton". Both are written, plus the RTL variant.
// ICU is built with the fixes in patches/, including the revision 34 Hntl rule.
//
// Usage:
//   icu-oracle info
//   icu-oracle skeleton-codepoints CONFUSABLES_TXT
//   icu-oracle skeleton-rtl-codepoints CONFUSABLES_TXT
//   icu-oracle nfd-codepoints
//   icu-oracle properties
//   icu-oracle strings CONFUSABLES_TXT INPUT
//   icu-oracle pairs CONFUSABLES_TXT INPUT

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include <unicode/brkiter.h>
#include <unicode/locid.h>
#include <unicode/normalizer2.h>
#include <unicode/uchar.h>
#include <unicode/uniset.h>
#include <unicode/unistr.h>
#include <unicode/uscript.h>
#include <unicode/uspoof.h>
#include <unicode/uversion.h>

// Internal ICU headers, for the resolved script set (UTS #39 section 5.1),
// which ICU computes but does not expose.
#include "scriptset.h"
#include "uspoof_impl.h"

namespace {

using icu::UnicodeSet;
using icu::UnicodeString;

[[noreturn]] void die(const std::string &what) {
  std::cerr << "icu-oracle: " << what << "\n";
  std::exit(2);
}

void check(UErrorCode status, const char *what) {
  if (U_FAILURE(status)) die(std::string(what) + ": " + u_errorName(status));
}

std::string hex(UChar32 c) {
  char buf[16];
  std::snprintf(buf, sizeof buf, "%04X", static_cast<unsigned>(c));
  return buf;
}

std::string hexSeq(const UnicodeString &s) {
  std::string out;
  for (int32_t i = 0; i < s.length();) {
    UChar32 c = s.char32At(i);
    if (!out.empty()) out += ' ';
    out += hex(c);
    i += U16_LENGTH(c);
  }
  return out;
}

UnicodeString parseSeq(const std::string &field) {
  UnicodeString s;
  std::istringstream in(field);
  std::string token;
  while (in >> token) {
    char *end = nullptr;
    unsigned long c = std::strtoul(token.c_str(), &end, 16);
    if (*end != '\0' || c > 0x10FFFF || (c >= 0xD800 && c <= 0xDFFF)) {
      die("bad code point: " + token);
    }
    s.append(static_cast<UChar32>(c));
  }
  return s;
}

std::vector<std::string> readLines(const char *path) {
  std::ifstream in(path);
  if (!in) die(std::string("cannot read ") + path);
  std::vector<std::string> lines;
  for (std::string line; std::getline(in, line);) {
    if (!line.empty() && line[0] == '#') continue;
    lines.push_back(line);
  }
  return lines;
}

std::string readFile(const char *path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) die(std::string("cannot read ") + path);
  return std::string(std::istreambuf_iterator<char>(in), {});
}

bool isSurrogate(UChar32 c) { return c >= 0xD800 && c <= 0xDFFF; }

// A spoof checker built from the pinned confusables.txt, so the mapping data
// is exactly the file the library is generated from.
struct Checker {
  USpoofChecker *sc;
  explicit Checker(const char *confusablesPath) {
    std::string source = readFile(confusablesPath);
    UErrorCode status = U_ZERO_ERROR;
    int32_t errorType = 0;
    UParseError parseError;
    sc = uspoof_openFromSource(source.data(), static_cast<int32_t>(source.size()),
                               nullptr, 0, &errorType, &parseError, &status);
    if (U_FAILURE(status)) {
      die(std::string("uspoof_openFromSource: ") + u_errorName(status) + " at line " +
          std::to_string(parseError.line));
    }
  }
  ~Checker() { uspoof_close(sc); }
  Checker(const Checker &) = delete;
  Checker &operator=(const Checker &) = delete;
};

// ICU's built-in checker, used only to confirm that the data ICU ships agrees
// with the pinned confusables.txt.
struct BuiltinChecker {
  USpoofChecker *sc;
  BuiltinChecker() {
    UErrorCode status = U_ZERO_ERROR;
    sc = uspoof_open(&status);
    check(status, "uspoof_open");
  }
  ~BuiltinChecker() { uspoof_close(sc); }
  BuiltinChecker(const BuiltinChecker &) = delete;
  BuiltinChecker &operator=(const BuiltinChecker &) = delete;
};

// internalSkeleton(X) in UTS #39 terms.
UnicodeString skeleton(const USpoofChecker *sc, const UnicodeString &s) {
  UErrorCode status = U_ZERO_ERROR;
  UnicodeString out;
  uspoof_getSkeletonUnicodeString(sc, 0, s, out, &status);
  check(status, "uspoof_getSkeletonUnicodeString");
  return out;
}

// bidiSkeleton(direction, X); skeleton(X) is bidiSkeleton(LTR, X).
UnicodeString bidiSkeleton(const USpoofChecker *sc, UBiDiDirection direction,
                           const UnicodeString &s) {
  UErrorCode status = U_ZERO_ERROR;
  UnicodeString out;
  uspoof_getBidiSkeletonUnicodeString(sc, direction, s, out, &status);
  check(status, "uspoof_getBidiSkeletonUnicodeString");
  return out;
}

// The resolved script set as sorted ISO 15924 codes, "ALL" for the set of all
// scripts, or "" for the empty set.
std::string resolvedScriptSet(const USpoofChecker *sc, const UnicodeString &s) {
  UErrorCode status = U_ZERO_ERROR;
  const icu::SpoofImpl *impl = icu::SpoofImpl::validateThis(sc, status);
  check(status, "SpoofImpl::validateThis");
  icu::ScriptSet set;
  impl->getResolvedScriptSet(s, set, status);
  check(status, "getResolvedScriptSet");
  // Only the all-scripts set contains Zyyy: Common characters resolve to ALL.
  if (set.test(USCRIPT_COMMON, status)) return "ALL";
  std::vector<std::string> names;
  for (int32_t i = set.nextSetBit(0); i >= 0; i = set.nextSetBit(i + 1)) {
    names.push_back(uscript_getShortName(static_cast<UScriptCode>(i)));
  }
  std::sort(names.begin(), names.end());
  std::string out;
  for (const auto &n : names) out += (out.empty() ? "" : " ") + n;
  return out;
}

// The General Security Profile: code points with Identifier_Status=Allowed.
UnicodeSet allowedSet() {
  UErrorCode status = U_ZERO_ERROR;
  UnicodeSet allowed;
  allowed.applyIntPropertyValue(UCHAR_IDENTIFIER_STATUS, U_ID_STATUS_ALLOWED, status);
  check(status, "applyIntPropertyValue(Identifier_Status)");
  allowed.freeze();
  return allowed;
}

const char *restrictionLevelName(URestrictionLevel level) {
  switch (level) {
    case USPOOF_ASCII: return "ASCII_ONLY";
    case USPOOF_SINGLE_SCRIPT_RESTRICTIVE: return "SINGLE_SCRIPT";
    case USPOOF_HIGHLY_RESTRICTIVE: return "HIGHLY_RESTRICTIVE";
    case USPOOF_MODERATELY_RESTRICTIVE: return "MODERATELY_RESTRICTIVE";
    case USPOOF_MINIMALLY_RESTRICTIVE: return "MINIMALLY_RESTRICTIVE";
    case USPOOF_UNRESTRICTIVE: return "UNRESTRICTED";
    default: die("unknown restriction level " + std::to_string(level));
  }
}

int info() {
  UVersionInfo icuVersion, unicodeVersion;
  char icuText[U_MAX_VERSION_STRING_LENGTH], unicodeText[U_MAX_VERSION_STRING_LENGTH];
  u_getVersion(icuVersion);
  u_getUnicodeVersion(unicodeVersion);
  u_versionToString(icuVersion, icuText);
  u_versionToString(unicodeVersion, unicodeText);
  std::cout << "icu\t" << icuText << "\n";
  std::cout << "unicode\t" << unicodeText << "\n";
  return 0;
}

int skeletonCodepoints(const char *confusablesPath) {
  Checker checker(confusablesPath);
  BuiltinChecker builtin;
  long mismatches = 0;
  for (UChar32 c = 0; c <= 0x10FFFF; ++c) {
    if (isSurrogate(c)) continue;
    UnicodeString in(c);
    UnicodeString out = skeleton(checker.sc, in);
    if (out != skeleton(builtin.sc, in)) {
      if (mismatches++ < 10) std::cerr << "built-in data differs at U+" << hex(c) << "\n";
    }
    // A lone character is never reordered or mirrored in an LTR paragraph, so
    // skeleton and internalSkeleton agree; the fixture relies on that.
    if (bidiSkeleton(checker.sc, UBIDI_LTR, in) != out) {
      die("bidiSkeleton(LTR) differs from internalSkeleton at U+" + hex(c));
    }
    if (out != in) std::cout << hex(c) << "\t" << hexSeq(out) << "\n";
  }
  if (mismatches) die("ICU's built-in confusables differ from the pinned file at " +
                      std::to_string(mismatches) + " code points");
  return 0;
}

// Code points whose RTL bidiSkeleton differs from their skeleton: mirrored
// characters, which a right-to-left paragraph displays as their mirror glyph.
int skeletonRtlCodepoints(const char *confusablesPath) {
  Checker checker(confusablesPath);
  for (UChar32 c = 0; c <= 0x10FFFF; ++c) {
    if (isSurrogate(c)) continue;
    UnicodeString in(c);
    UnicodeString rtl = bidiSkeleton(checker.sc, UBIDI_RTL, in);
    if (rtl != skeleton(checker.sc, in)) std::cout << hex(c) << "\t" << hexSeq(rtl) << "\n";
  }
  return 0;
}

int nfdCodepoints() {
  UErrorCode status = U_ZERO_ERROR;
  const icu::Normalizer2 *nfd = icu::Normalizer2::getNFDInstance(status);
  check(status, "getNFDInstance");
  for (UChar32 c = 0; c <= 0x10FFFF; ++c) {
    if (isSurrogate(c)) continue;
    UnicodeString in(c);
    UnicodeString out = nfd->normalize(in, status);
    check(status, "normalize");
    if (out != in) std::cout << hex(c) << "\t" << hexSeq(out) << "\n";
  }
  return 0;
}

// Writes one property as UCD-style ranges, omitting code points whose value
// equals the default.
template <typename ValueOf>
void dumpProperty(const char *name, const std::string &defaultValue, ValueOf valueOf) {
  std::cout << "## " << name << "\tdefault=" << defaultValue << "\n";
  UChar32 start = 0;
  std::string current = valueOf(0);
  auto flush = [&](UChar32 end) {
    if (current == defaultValue) return;
    std::cout << hex(start);
    if (end != start) std::cout << ".." << hex(end);
    std::cout << "\t" << current << "\n";
  };
  for (UChar32 c = 1; c <= 0x110000; ++c) {
    std::string value = c <= 0x10FFFF ? valueOf(c) : std::string("\x01");
    if (value != current) {
      flush(c - 1);
      start = c;
      current = value;
    }
  }
}

std::string binary(UChar32 c, UProperty property) {
  return u_hasBinaryProperty(c, property) ? "Y" : "N";
}

std::string enumName(UChar32 c, UProperty property, UPropertyNameChoice choice) {
  const char *name = u_getPropertyValueName(property, u_getIntPropertyValue(c, property), choice);
  if (name == nullptr) die("unnamed property value");
  return name;
}

std::string scriptExtensions(UChar32 c) {
  UErrorCode status = U_ZERO_ERROR;
  UScriptCode scripts[256];
  int32_t count = uscript_getScriptExtensions(c, scripts, 256, &status);
  check(status, "uscript_getScriptExtensions");
  std::vector<std::string> names;
  for (int32_t i = 0; i < count; ++i) names.push_back(uscript_getShortName(scripts[i]));
  std::sort(names.begin(), names.end());
  std::string out;
  for (const auto &n : names) out += (out.empty() ? "" : " ") + n;
  return out;
}

std::string identifierTypes(UChar32 c) {
  UErrorCode status = U_ZERO_ERROR;
  UIdentifierType types[16];
  int32_t count = u_getIDTypes(c, types, 16, &status);
  check(status, "u_getIDTypes");
  std::vector<std::string> names;
  for (int32_t i = 0; i < count; ++i) {
    names.push_back(u_getPropertyValueName(UCHAR_IDENTIFIER_TYPE, types[i], U_LONG_PROPERTY_NAME));
  }
  std::sort(names.begin(), names.end());
  std::string out;
  for (const auto &n : names) out += (out.empty() ? "" : " ") + n;
  return out;
}

int properties() {
  dumpProperty("Script", "Zzzz", [](UChar32 c) {
    UErrorCode status = U_ZERO_ERROR;
    UScriptCode script = uscript_getScript(c, &status);
    check(status, "uscript_getScript");
    return std::string(uscript_getShortName(script));
  });
  // Only where Script_Extensions differs from {Script}, as in ScriptExtensions.txt.
  dumpProperty("Script_Extensions", "", [](UChar32 c) {
    UErrorCode status = U_ZERO_ERROR;
    UScriptCode script = uscript_getScript(c, &status);
    check(status, "uscript_getScript");
    std::string scx = scriptExtensions(c);
    return scx == uscript_getShortName(script) ? std::string() : scx;
  });
  dumpProperty("General_Category", "Cn",
               [](UChar32 c) { return enumName(c, UCHAR_GENERAL_CATEGORY, U_SHORT_PROPERTY_NAME); });
  dumpProperty("Canonical_Combining_Class", "0", [](UChar32 c) {
    return std::to_string(u_getCombiningClass(c));
  });
  dumpProperty("XID_Start", "N", [](UChar32 c) { return binary(c, UCHAR_XID_START); });
  dumpProperty("XID_Continue", "N", [](UChar32 c) { return binary(c, UCHAR_XID_CONTINUE); });
  dumpProperty("Default_Ignorable_Code_Point", "N",
               [](UChar32 c) { return binary(c, UCHAR_DEFAULT_IGNORABLE_CODE_POINT); });
  dumpProperty("Bidi_Control", "N", [](UChar32 c) { return binary(c, UCHAR_BIDI_CONTROL); });
  dumpProperty("Join_Control", "N", [](UChar32 c) { return binary(c, UCHAR_JOIN_CONTROL); });
  dumpProperty("Extended_Pictographic", "N",
               [](UChar32 c) { return binary(c, UCHAR_EXTENDED_PICTOGRAPHIC); });
  dumpProperty("Grapheme_Cluster_Break", "Other",
               [](UChar32 c) { return enumName(c, UCHAR_GRAPHEME_CLUSTER_BREAK, U_LONG_PROPERTY_NAME); });
  dumpProperty("Indic_Conjunct_Break", "None",
               [](UChar32 c) { return enumName(c, UCHAR_INDIC_CONJUNCT_BREAK, U_LONG_PROPERTY_NAME); });
  dumpProperty("Identifier_Status", "Restricted",
               [](UChar32 c) { return enumName(c, UCHAR_IDENTIFIER_STATUS, U_LONG_PROPERTY_NAME); });
  dumpProperty("Identifier_Type", "Not_Character", identifierTypes);
  dumpProperty("Bidi_Class", "L",
               [](UChar32 c) { return enumName(c, UCHAR_BIDI_CLASS, U_SHORT_PROPERTY_NAME); });
  dumpProperty("Bidi_Mirroring_Glyph", "", [](UChar32 c) {
    UChar32 mirror = u_charMirror(c);
    return mirror == c ? std::string() : hex(mirror);
  });
  dumpProperty("Bidi_Paired_Bracket_Type", "None", [](UChar32 c) {
    return enumName(c, UCHAR_BIDI_PAIRED_BRACKET_TYPE, U_LONG_PROPERTY_NAME);
  });
  dumpProperty("Bidi_Paired_Bracket", "", [](UChar32 c) {
    UChar32 paired = u_getBidiPairedBracket(c);
    return paired == c ? std::string() : hex(paired);
  });
  return 0;
}

std::vector<int32_t> graphemeBoundaries(const UnicodeString &s) {
  UErrorCode status = U_ZERO_ERROR;
  std::unique_ptr<icu::BreakIterator> it(
      icu::BreakIterator::createCharacterInstance(icu::Locale::getRoot(), status));
  check(status, "createCharacterInstance");
  it->setText(s);
  std::vector<int32_t> out;
  for (int32_t b = it->first(); b != icu::BreakIterator::DONE; b = it->next()) {
    out.push_back(s.countChar32(0, b));
  }
  return out;
}

int strings(const char *confusablesPath, const char *inputPath) {
  Checker checker(confusablesPath);
  BuiltinChecker builtin;
  UErrorCode status = U_ZERO_ERROR;
  const icu::Normalizer2 *nfd = icu::Normalizer2::getNFDInstance(status);
  check(status, "getNFDInstance");

  UnicodeSet allowed = allowedSet();
  uspoof_setAllowedUnicodeSet(checker.sc, &allowed, &status);
  check(status, "uspoof_setAllowedUnicodeSet");
  uspoof_setChecks(checker.sc,
                   USPOOF_RESTRICTION_LEVEL | USPOOF_CHAR_LIMIT | USPOOF_INVISIBLE |
                       USPOOF_MIXED_NUMBERS | USPOOF_HIDDEN_OVERLAY | USPOOF_AUX_INFO,
                   &status);
  check(status, "uspoof_setChecks");
  USpoofCheckResult *result = uspoof_openCheckResult(&status);
  check(status, "uspoof_openCheckResult");

  for (const std::string &line : readLines(inputPath)) {
    UnicodeString s = parseSeq(line);
    UnicodeString internal = skeleton(checker.sc, s);
    if (internal != skeleton(builtin.sc, s)) die("built-in skeleton differs for " + line);
    UnicodeString ltr = bidiSkeleton(checker.sc, UBIDI_LTR, s);
    UnicodeString rtl = bidiSkeleton(checker.sc, UBIDI_RTL, s);
    UnicodeString normalized = nfd->normalize(s, status);
    check(status, "normalize");

    uspoof_check2UnicodeString(checker.sc, s, result, &status);
    check(status, "uspoof_check2UnicodeString");
    int32_t checks = uspoof_getCheckResultChecks(result, &status);
    URestrictionLevel level = uspoof_getCheckResultRestrictionLevel(result, &status);
    const USet *numerics = uspoof_getCheckResultNumerics(result, &status);
    check(status, "uspoof check result");

    std::string failed;
    auto flag = [&](int32_t bit, const char *name) {
      if (checks & bit) failed += (failed.empty() ? "" : " ") + std::string(name);
    };
    flag(USPOOF_CHAR_LIMIT, "CHAR_LIMIT");
    flag(USPOOF_INVISIBLE, "INVISIBLE");
    flag(USPOOF_MIXED_NUMBERS, "MIXED_NUMBERS");
    flag(USPOOF_HIDDEN_OVERLAY, "HIDDEN_OVERLAY");

    std::string zeros;
    const UnicodeSet *zeroSet = UnicodeSet::fromUSet(numerics);
    for (int32_t i = 0; i < zeroSet->size(); ++i) {
      zeros += (zeros.empty() ? "" : " ") + hex(zeroSet->charAt(i));
    }

    std::string boundaries;
    for (int32_t b : graphemeBoundaries(s)) {
      boundaries += (boundaries.empty() ? "" : " ") + std::to_string(b);
    }

    std::cout << hexSeq(ltr) << "\t" << hexSeq(internal) << "\t" << hexSeq(rtl) << "\t"
              << hexSeq(normalized) << "\t" << resolvedScriptSet(checker.sc, s) << "\t"
              << restrictionLevelName(level) << "\t" << failed << "\t" << zeros << "\t"
              << boundaries << "\n";
  }
  uspoof_closeCheckResult(result);
  return 0;
}

int pairs(const char *confusablesPath, const char *inputPath) {
  Checker checker(confusablesPath);
  UErrorCode status = U_ZERO_ERROR;
  uspoof_setChecks(checker.sc, USPOOF_CONFUSABLE, &status);
  check(status, "uspoof_setChecks");
  for (const std::string &line : readLines(inputPath)) {
    std::size_t tab = line.find('\t');
    if (tab == std::string::npos) die("pair without a tab: " + line);
    UnicodeString a = parseSeq(line.substr(0, tab));
    UnicodeString b = parseSeq(line.substr(tab + 1));
    auto kinds = [](int32_t bits) {
      std::string out;
      auto flag = [&](int32_t bit, const char *name) {
        if (bits & bit) out += (out.empty() ? "" : " ") + std::string(name);
      };
      flag(USPOOF_SINGLE_SCRIPT_CONFUSABLE, "SINGLE_SCRIPT");
      flag(USPOOF_MIXED_SCRIPT_CONFUSABLE, "MIXED_SCRIPT");
      flag(USPOOF_WHOLE_SCRIPT_CONFUSABLE, "WHOLE_SCRIPT");
      return out;
    };
    int32_t ltr = uspoof_areBidiConfusableUnicodeString(checker.sc, UBIDI_LTR, a, b, &status);
    int32_t internal = uspoof_areConfusableUnicodeString(checker.sc, a, b, &status);
    int32_t rtl = uspoof_areBidiConfusableUnicodeString(checker.sc, UBIDI_RTL, a, b, &status);
    check(status, "uspoof_are*Confusable");
    std::cout << kinds(ltr) << "\t" << kinds(internal) << "\t" << kinds(rtl) << "\n";
  }
  return 0;
}

}  // namespace

int main(int argc, char **argv) {
  std::ios::sync_with_stdio(false);
  std::string mode = argc > 1 ? argv[1] : "";
  if (mode == "info" && argc == 2) return info();
  if (mode == "skeleton-codepoints" && argc == 3) return skeletonCodepoints(argv[2]);
  if (mode == "skeleton-rtl-codepoints" && argc == 3) return skeletonRtlCodepoints(argv[2]);
  if (mode == "nfd-codepoints" && argc == 2) return nfdCodepoints();
  if (mode == "properties" && argc == 2) return properties();
  if (mode == "strings" && argc == 4) return strings(argv[2], argv[3]);
  if (mode == "pairs" && argc == 4) return pairs(argv[2], argv[3]);
  std::cerr << "usage: icu-oracle info | skeleton-codepoints CONFUSABLES |"
               " skeleton-rtl-codepoints CONFUSABLES | nfd-codepoints | properties |"
               " strings CONFUSABLES INPUT | pairs CONFUSABLES INPUT\n";
  return 64;
}
