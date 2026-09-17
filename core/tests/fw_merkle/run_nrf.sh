#!/usr/bin/env bash
# Build + run the nRF founder-tree cross-validation: the STM's nrf_image.c, the
# nRF's mcuboot image_pq.c (PQ_HOST_TEST, same host SHA-256) and the host
# signer's vectors (gen_nrf_vector.py -> nrf_tree.py) must agree byte-for-byte.
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
if [[ ! -f "$mcuboot/boot/bootutil/src/image_pq.c" ]]; then
  echo "SKIP: $mcuboot has no boot/bootutil/src/image_pq.c -- the checkout is not" >&2
  echo "      on the PQ branch. west leaves it at the upstream revision; this test" >&2
  echo "      needs origin/tychovrahe/trezor-ncs3.3.0/pq2 checked out there." >&2
  exit 1
fi

# sphincsplus' params.h needs PARAMS; must match boot/zephyr/CMakeLists.txt.
params=sphincs-sha2-128s

echo "== generating nRF vector =="
PYTHONPATH="$core/tools" python "$here/gen_nrf_vector.py" "$vec"

echo "== compiling nrf_crossvalidate =="
# Ed25519 is the monorepo's trezor-crypto, the copy boot_header.c links on device.
# --gc-sections: image_pq.c pulls in SLH-DSA that this harness never calls.
gcc -O2 -Wall -Wextra \
    -DPQ_HOST_TEST -DPARAMS="$params" -DMODEL_IDENTIFIER=0x31573354 \
    -ffunction-sections -fdata-sections \
    -I "$here" -I "$core/embed/sec/image" -I "$core/embed/sec/image/inc" \
    -I "$core/embed/io/nrf" -I "$core/embed/io/nrf/inc" \
    -I "$crypto" -I "$(dirname "$vec")" \
    -I "$mcuboot/boot/bootutil/include" -I "$here/fih_host" \
    -I "$mcuboot/ext/sphincsplus" \
    "$here/nrf_crossvalidate.c" \
    -include "$here/shims_nrf.h" "$core/embed/sec/image/boot_header_merkle.c" \
    -include "$here/shims_nrf.h" "$core/embed/io/nrf/nrf_image.c" \
    "$mcuboot/boot/bootutil/src/image_pq.c" \
    "$here/fih_host.c" "$crypto/sha2.c" "$crypto/memzero.c" \
    "$crypto/consteq.c" "$crypto"/ed25519-donna/*.c \
    -Wl,--gc-sections -o "$out"

echo "== nRF founder-tree cross-validation =="
"$out"
