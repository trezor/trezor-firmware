#!/usr/bin/env bash
# Build + run the consent-digest cross-validation: the real sec/image sources
# (bootloader view vs firmware view), then trezorlib's host builder against it.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
core="$(cd "$here/../.." && pwd)"
crypto="$core/../crypto"
out="${TMPDIR:-/tmp}/consent_test"

# The device sources under test (sec/image), compiled verbatim.
sec=("$core/embed/sec/image/merkle.c" "$core/embed/sec/image/firmware_manifest.c"
     "$core/embed/sec/image/fw_variant.c" "$core/embed/sec/image/boot_header_consent.c")
echo "== compiling consent_test =="
# shims.h is forced in with -include so the device source keeps its normal
# include block for the real build.
gcc -O2 -Wall -Wextra \
    -I "$here" -I "$core/embed/sec/image" -I "$crypto" \
    "$here/consent_test.c" \
    -include "$here/shims.h" "${sec[@]}" \
    "$crypto/sha2.c" "$crypto/memzero.c" -o "$out"

vecdir="${TMPDIR:-/tmp}/consent_vector"
mkdir -p "$vecdir"

echo "== consent digest cross-validation (device code) =="
"$out" "$vecdir"

# A host/device disagreement here refuses every interaction-less upgrade.
echo "== host builder vs device (trezorlib.firmware.pq_secure) =="
python "$here/consent_host_check.py" "$vecdir"
