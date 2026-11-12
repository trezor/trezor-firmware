#!/usr/bin/env bash
# Builds trezor_tests (Monero's Trezor test harness used by
# run_tests_device_emu_monero.sh) from the vendor/monero submodule commit with
# the patches in patches/, if any. Needs git and docker. The submodule does not
# need to be checked out: its commit is fetched from its URL.
#
# The build inputs are the submodule commit and this directory: CI caches the
# binary under both (see docs/tests/monero-tests.md).
#
# Usage: build.sh [OUTPUT]
# Writes OUTPUT and OUTPUT.sha256. The default OUTPUT is where the run script
# looks for the binary.

set -euo pipefail

# Base image of docker/tests/Dockerfile, pinned by digest.
BASE_IMAGE=ubuntu:18.04@sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [OUTPUT]" >&2
  exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
# The base: URL from .gitmodules, commit from the index (a staged pin change counts).
BASE_URL="$(git -C "$REPO" config -f .gitmodules submodule.vendor/monero.url)"
BASE_COMMIT="$(git -C "$REPO" ls-files -s vendor/monero | cut -d' ' -f2)"
echo "Base: $BASE_URL $BASE_COMMIT"
OUTPUT="${1:-$REPO/core/tests/trezor_monero_tests}"
mkdir -p "$(dirname "$OUTPUT")"
OUT_DIR="$(cd "$(dirname "$OUTPUT")" && pwd)"
OUT_NAME="$(basename "$OUTPUT")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

git -C "$WORK" init -q monero
SRC="$WORK/monero"
git -C "$SRC" fetch -q --depth 1 "$BASE_URL" "$BASE_COMMIT"
git -C "$SRC" checkout -q FETCH_HEAD
git -C "$SRC" submodule update -q --init --recursive --depth 1
shopt -s nullglob
patches=("$HERE"/patches/*.patch)
if [[ ${#patches[@]} -gt 0 ]]; then
  git -C "$SRC" apply "${patches[@]}"
fi

# Ubuntu 18.04 image with statically built dependencies, see docker/README.md.
# x86-64 on every host, emulated on Apple Silicon.
docker build --platform linux/amd64 -f "$SRC/docker/tests/Dockerfile" --build-arg BASE_IMAGE="$BASE_IMAGE" -t monero-trezor-tests "$SRC"

# Debug build includes the UDP transport for the emulator.
# ARCH=default: no -march, the default "native" would target the build machine's CPU.
# The binary is checked in the container, the host may not be Linux.
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" -e HOME=/tmp -e OUT_NAME="$OUT_NAME" \
  -v "$SRC:/src" -v "$OUT_DIR:/out" -w /src monero-trezor-tests bash -c '
  set -ex
  mkdir -p build/debug
  cd build/debug
  cmake -D BUILD_TESTS=ON -D TREZOR_DEBUG=ON -D STATIC=ON -D MANUAL_SUBMODULES=1 \
    -D CMAKE_BUILD_TYPE=Debug -D ARCH=default ../..
  make -j"$(nproc)" trezor_tests

  BIN=/src/build/debug/tests/trezor/trezor_tests
  # Only libc-family libraries may be dynamic, the run script patches the interpreter under nix.
  if readelf -d "$BIN" | grep NEEDED | grep -vE "\[(libc|libm|libdl|libpthread|librt|ld-linux-x86-64)\.so"; then
    echo "Unexpected dynamic dependencies" >&2
    exit 1
  fi
  (cd /tmp && "$BIN" --help > /dev/null)

  cp "$BIN" "/out/$OUT_NAME"
  cd /out
  sha256sum "$OUT_NAME" > "$OUT_NAME.sha256"
  cat "$OUT_NAME.sha256"
'
