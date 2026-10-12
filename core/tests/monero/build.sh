#!/usr/bin/env bash
# Builds trezor_tests (Monero's Trezor test harness used by
# run_tests_device_emu_monero.sh) from the base below with the patches in
# patches/, if any. Needs git and docker.
#
# Every input of the build is in this directory: CI caches the binary under a
# hash of it (see docs/tests/monero-tests.md).
#
# Usage: build.sh OUTDIR
# Writes OUTDIR/trezor_tests and OUTDIR/trezor_tests.sha256.

set -euo pipefail

# Pin the base by commit (tags can move): tag v0.18.3.1-dev-tests-u18.04-01.
BASE_URL=https://github.com/ph4r05/monero.git
BASE_COMMIT=d9d6a6af310aba9dc1fac8592856f5e3464496c3
# Base image of docker/tests/Dockerfile, pinned by digest.
BASE_IMAGE=ubuntu:18.04@sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 OUTDIR" >&2
  exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$1"
OUT="$(cd "$1" && pwd)"
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
docker build -f "$SRC/docker/tests/Dockerfile" --build-arg BASE_IMAGE="$BASE_IMAGE" -t monero-trezor-tests "$SRC"

# Debug build includes the UDP transport for the emulator.
# ARCH=default: no -march, the default "native" would target the build machine's CPU.
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$SRC:/src" -w /src monero-trezor-tests bash -c '
  set -ex
  mkdir -p build/debug
  cd build/debug
  cmake -D BUILD_TESTS=ON -D TREZOR_DEBUG=ON -D STATIC=ON -D MANUAL_SUBMODULES=1 \
    -D CMAKE_BUILD_TYPE=Debug -D ARCH=default ../..
  make -j"$(nproc)" trezor_tests
'

BIN="$SRC/build/debug/tests/trezor/trezor_tests"
# Only libc-family libraries may be dynamic, the run script patches the interpreter under nix.
if readelf -d "$BIN" | grep NEEDED | grep -vE '\[(libc|libm|libdl|libpthread|librt|ld-linux-x86-64)\.so'; then
  echo "Unexpected dynamic dependencies" >&2
  exit 1
fi
(cd "$WORK" && "$BIN" --help > /dev/null)

cp "$BIN" "$OUT/trezor_tests"
(cd "$OUT" && sha256sum trezor_tests > trezor_tests.sha256)
cat "$OUT/trezor_tests.sha256"
