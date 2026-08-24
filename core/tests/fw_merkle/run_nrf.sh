#!/usr/bin/env bash
# Build + run the nRF founder-tree cross-validation harness.
#
# Compiles THREE implementations of the same construction against one another:
#
#   - the STM's  (embed/io/nrf/nrf_image.c) with a host SHA-256
#   - the nRF's  (mcuboot boot/bootutil/src/image_pq.c, built with PQ_HOST_TEST so
#                 it uses the same hash backend -- so this compares implementations,
#                 not hash libraries)
#   - the host signer's (tools/trezor_core_tools/nrf_tree.py), which produces the
#                 vectors via gen_nrf_vector.py
#
# The leaf is MCUboot's own image hash, so all three must agree byte-for-byte; a
# mismatch is otherwise silent (images just stop verifying).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
core="$(cd "$here/../.." && pwd)"
crypto="$core/../crypto"
mcuboot="$core/../nordic/bootloader/mcuboot"
out="${TMPDIR:-/tmp}/nrf_crossvalidate"
vec="${TMPDIR:-/tmp}/nrf_vector.h"

if [[ ! -d "$mcuboot" ]]; then
  echo "SKIP: $mcuboot is absent (west-managed; run 'west update' in nordic/)" >&2
  exit 1
fi

# sphincsplus' params.h needs PARAMS defined by any TU that includes it; mcuboot's
# own build sets the same value (boot/zephyr/CMakeLists.txt).
params=sphincs-sha2-128s

echo "== generating nRF vector =="
PYTHONPATH="$core/tools" python "$here/gen_nrf_vector.py" "$vec"

echo "== compiling nrf_crossvalidate =="
# Ed25519 comes from the MONOREPO's trezor-crypto, not mcuboot's: the code under
# test here is the STM's, and boot_header.c links exactly this copy on device.
# --gc-sections: image_pq.c pulls in SLH-DSA for pq_image_verify, which this harness
# does not call -- without it the link fails on that unused crypto.
gcc -O2 -Wall -Wextra \
    -DPQ_HOST_TEST -DPARAMS="$params" \
    -ffunction-sections -fdata-sections \
    -I "$here" -I "$core/embed/sec/image/stm32" -I "$core/embed/sec/image/inc" \
    -I "$core/embed/io/nrf" -I "$core/embed/io/nrf/inc" \
    -I "$crypto" -I "$(dirname "$vec")" \
    -I "$mcuboot/boot/bootutil/include" -I "$here/fih_host" \
    -I "$mcuboot/ext/sphincsplus" \
    "$here/nrf_crossvalidate.c" \
    -include "$here/shims_nrf.h" "$core/embed/sec/image/stm32/boot_header_merkle.c" \
    -include "$here/shims_nrf.h" "$core/embed/io/nrf/nrf_image.c" \
    "$mcuboot/boot/bootutil/src/image_pq.c" \
    "$here/fih_host.c" "$crypto/sha2.c" "$crypto/memzero.c" \
    "$crypto/consteq.c" "$crypto"/ed25519-donna/*.c \
    -Wl,--gc-sections -o "$out"

echo "== nRF founder-tree cross-validation =="
"$out"
