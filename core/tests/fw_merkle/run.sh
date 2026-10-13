#!/usr/bin/env bash
# Build + run the firmware Merkle-tree cross-validation harness: the real
# sec/image Merkle sources against the FWM3 vector produced by the Python signer.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
core="$(cd "$here/../.." && pwd)"
crypto="$core/../crypto"
out="${TMPDIR:-/tmp}/crossvalidate"
vec="${TMPDIR:-/tmp}/multivariant.vec"

# The device sources under test (sec/image), compiled verbatim.
sec=("$core/embed/sec/image/merkle.c" "$core/embed/sec/image/firmware_manifest.c"
     "$core/embed/sec/image/fw_variant.c" "$core/embed/sec/image/boot_header_consent.c")
echo "== compiling crossvalidate =="
# shims.h is forced in with -include so the device source keeps its normal
# include block for the real build.
gcc -O2 -Wall -Wextra \
    -I "$here" -I "$core/embed/sec/image" -I "$core/embed/sec/image/inc" \
    -I "$crypto" \
    "$here/crossvalidate.c" \
    -include "$here/shims.h" "${sec[@]}" \
    "$crypto/sha2.c" "$crypto/memzero.c" -o "$out"

echo "== generating multi-variant vector =="
python "$here/gen_multivariant.py" "$vec"

echo "== FWM3 (manifest) cross-validation =="
"$out" "$vec"

# Optional: replay an additional FWM3 vector produced by the signer.
if [[ "${1:-}" != "" ]]; then
  echo "== FWM3 cross-validation ($1) =="
  "$out" "$1"
fi
