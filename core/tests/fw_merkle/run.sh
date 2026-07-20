#!/usr/bin/env bash
# Build + run the firmware Merkle-tree cross-validation harness.
#
# Compiles the *real* on-device tree math (embed/sec/image/stm32/boot_header_merkle.h)
# against a host SHA-256 and replays vectors produced by the Python signer, so the
# on-device and host implementations are proven byte-identical.
#
#   FWM2: multi-variant founder firmware_root + per-variant proofs over full
#         firmware images [manifest | module code...] (synthetic, generated here).
#         Replayed through the real device firmware_verify_manifest.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
core="$(cd "$here/../.." && pwd)"
crypto="$core/../crypto"
out="${TMPDIR:-/tmp}/crossvalidate"
vec="${TMPDIR:-/tmp}/multivariant.vec"

echo "== compiling crossvalidate =="
gcc -O2 -Wall -Wextra \
    -I "$core/embed/sec/image/stm32" -I "$crypto" \
    "$here/crossvalidate.c" "$crypto/sha2.c" "$crypto/memzero.c" -o "$out"

echo "== generating multi-variant vector =="
python "$here/gen_multivariant.py" "$vec"

echo "== FWM2 (manifest) cross-validation =="
"$out" "$vec"

# Optional: replay an additional FWM2 vector produced by the signer.
if [[ "${1:-}" != "" ]]; then
  echo "== FWM2 cross-validation ($1) =="
  "$out" "$1"
fi
