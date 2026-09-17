#!/usr/bin/env bash
# Build + run the founder signature harness (pq_sig_test.c): mcuboot's
# pq_image_verify against real SLH-DSA + Ed25519 signatures. Slow (~2 min of
# keygen). Links mcuboot's own vendored trezor-crypto, which is what the nRF
# actually compiles.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
core="$(cd "$here/../.." && pwd)"
mcuboot="$core/../nordic/bootloader/mcuboot"
sphincs="$mcuboot/ext/sphincsplus/ref"
tc="$mcuboot/boot/bootutil/trezor-crypto"
out="${TMPDIR:-/tmp}/pq_sig_test"

if [[ ! -d "$mcuboot" ]]; then
  echo "SKIP: $mcuboot is absent (west-managed; run 'west update' in nordic/)" >&2
  exit 1
fi
if [[ ! -f "$sphincs/sign.c" ]]; then
  echo "SKIP: $sphincs is empty (mcuboot's ext/sphincsplus submodule not checked out)" >&2
  exit 1
fi
if [[ ! -f "$mcuboot/boot/bootutil/src/image_pq.c" ]]; then
  echo "SKIP: $mcuboot has no boot/bootutil/src/image_pq.c -- the checkout is not" >&2
  echo "      on the PQ branch. west leaves it at the upstream revision; this test" >&2
  echo "      needs origin/tychovrahe/trezor-ncs3.3.0/pq2 checked out there." >&2
  exit 1
fi

params=sphincs-sha2-128s

echo "== compiling pq_sig_test =="
# -w: the reference sphincsplus and MCUboot's FIH headers are noisy.
# --gc-sections: drops ed25519-donna's curve25519 / rand paths, never called here.
gcc -O2 -w \
    -DPQ_HOST_TEST -DPARAMS="$params" -DMODEL_IDENTIFIER=0x31573354 \
    -ffunction-sections -fdata-sections \
    -I "$mcuboot/boot/bootutil/include" -I "$mcuboot" -I "$here/fih_host" \
    -I "$mcuboot/ext/sphincsplus" -I "$tc" -I "$tc/ed25519-donna" \
    "$here/pq_sig_test.c" "$mcuboot/boot/bootutil/src/image_pq.c" "$here/fih_host.c" \
    "$sphincs/address.c" "$sphincs/fors.c" "$sphincs/hash_sha2.c" \
    "$sphincs/merkle.c" "$sphincs/sha2.c" "$sphincs/sign.c" \
    "$sphincs/thash_sha2_simple.c" "$sphincs/utils.c" "$sphincs/utilsx1.c" \
    "$sphincs/wots.c" "$sphincs/wotsx1.c" "$sphincs/fips202.c" \
    "$tc/sha2.c" "$tc/memzero.c" "$tc/consteq.c" "$tc"/ed25519-donna/*.c \
    -Wl,--gc-sections -o "$out"

echo "== founder signature verification =="
"$out"
