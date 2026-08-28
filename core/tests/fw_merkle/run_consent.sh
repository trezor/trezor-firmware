#!/usr/bin/env bash
# Build + run the interaction-less upgrade consent-digest cross-validation.
#
# Compiles the *real* on-device implementation (embed/sec/image/stm32/
# boot_header_merkle.c) against a host SHA-256 and checks that the two views of
# the same release agree: the BOOTLOADER's, computed from a full boot header in
# flash, and FIRMWARE's, computed from just the prefix it receives over the wire.
# Also pins the invariance that makes that possible -- the digest must not move
# when the bootloader rewrites firmware_type while staging -- and that it still
# changes with everything consent has to pin.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
core="$(cd "$here/../.." && pwd)"
crypto="$core/../crypto"
out="${TMPDIR:-/tmp}/consent_test"

echo "== compiling consent_test =="
# The device source is COMPILED, not textually included: shims.h is forced in so
# it keeps its normal include block for the real build.
gcc -O2 -Wall -Wextra \
    -I "$here" -I "$core/embed/sec/image/stm32" -I "$crypto" \
    "$here/consent_test.c" \
    -include "$here/shims.h" "$core/embed/sec/image/stm32/boot_header_merkle.c" \
    "$crypto/sha2.c" "$crypto/memzero.c" -o "$out"

vecdir="${TMPDIR:-/tmp}/consent_vector"
mkdir -p "$vecdir"

echo "== consent digest cross-validation (device code) =="
"$out" "$vecdir"

# The host builder must agree, or every interaction-less upgrade gets refused:
# the host would confirm one release and the device would digest it differently.
echo "== host builder vs device (trezor_core_tools) =="
python "$here/consent_host_check.py" "$vecdir"
