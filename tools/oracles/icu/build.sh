#!/usr/bin/env bash
# Build a pinned ICU release from source with patches/*.patch applied, then
# compile the oracle against it.
#
# The ICU build is cached in $ICU_BUILD_DIR (default: .build next to this
# script), keyed by the ICU version and the patches, and reused while both stay
# the same. Prints the path of the oracle binary on success.
set -euo pipefail

ICU_VERSION=79.1rc
ICU_TAG=release-79.1rc
# Matches the digest GitHub records for the release asset.
ICU_SHA256=9d9891c0e753801d4fb640d1bfd2310b318d267bd47b8e7461e39d547bbb3146

here=$(cd "$(dirname "$0")" && pwd)
build=${ICU_BUILD_DIR:-$here/.build}
tarball=$build/icu4c-$ICU_VERSION-sources.tgz
jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)

sha256() {
  python3 -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}

patch_id=$(cat "$here"/patches/*.patch | python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:12])')
prefix=$build/icu-$ICU_VERSION-$patch_id

mkdir -p "$build"
if [ ! -f "$prefix/lib/libicui18n.a" ]; then
  if [ ! -f "$tarball" ] || [ "$(sha256 "$tarball")" != "$ICU_SHA256" ]; then
    curl --fail --silent --show-error --location --output "$tarball" \
      "https://github.com/unicode-org/icu/releases/download/$ICU_TAG/icu4c-$ICU_VERSION-sources.tgz"
  fi
  actual=$(sha256 "$tarball")
  if [ "$actual" != "$ICU_SHA256" ]; then
    echo "ICU tarball hash mismatch: expected $ICU_SHA256, got $actual" >&2
    exit 1
  fi
  rm -rf "$build/src"
  mkdir -p "$build/src"
  tar -xzf "$tarball" -C "$build/src"
  for p in "$here"/patches/*.patch; do
    patch --quiet --directory="$build/src/icu" --strip=1 <"$p"
  done
  (
    cd "$build/src/icu/source"
    ./configure --prefix="$prefix" --enable-static --disable-shared \
      --disable-tests --disable-samples --disable-extras --disable-icuio \
      --disable-layoutex >"$build/configure.log" 2>&1
    make -j"$jobs" >"$build/make.log" 2>&1
    make install >"$build/install.log" 2>&1
  )
  # The oracle reads resolved script sets through ICU's internal SpoofImpl,
  # so keep the internal headers next to the installed ones.
  mkdir -p "$prefix/internal"
  cp "$build/src/icu/source/common/"*.h "$build/src/icu/source/i18n/"*.h "$prefix/internal/"
fi

c++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$prefix/include" -isystem "$prefix/internal" \
  "$here/oracle.cpp" -o "$build/icu-oracle" \
  -L"$prefix/lib" -licui18n -licuuc -licudata -lpthread -lm
echo "$build/icu-oracle"
