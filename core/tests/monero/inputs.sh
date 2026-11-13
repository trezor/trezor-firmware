#!/usr/bin/env bash
# Prints the ID of the trezor_tests build inputs: the vendor/monero submodule
# commit, build.sh and the patches. build.sh and download.sh record it next to
# the binary, prepare.sh replaces a binary whose ID differs, and CI uses it as
# the cache key and the artifact name.
#
# To force a rebuild, change build.sh.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
# Commit from the index, as in build.sh.
BASE_COMMIT="$(git -C "$REPO" ls-files -s vendor/monero | cut -d' ' -f2)"
FILES_HASH="$(
  cd "$HERE"
  { echo build.sh; if [[ -d patches ]]; then find patches -type f; fi; } | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-16
)"
echo "${BASE_COMMIT:0:12}-$FILES_HASH"
