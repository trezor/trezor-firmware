#!/usr/bin/env bash
# Build + run the founder signature harness (pq_sig_test.c).
#
# End-to-end test of the nRF's own founder verification (mcuboot
# boot/bootutil/src/image_pq.c) against REAL signatures: it generates its own key
# pool, builds a PQ-native MCUboot image, signs modelRoot exactly as the founder
# would, and checks pq_image_verify accepts it and rejects every tampering.
#
# Slow (~2 min): SLH-DSA keygen for 3 keypairs dominates.
#
# Unlike run_nrf.sh this needs the REAL crypto, and it deliberately uses MCUboot's
# OWN vendored trezor-crypto rather than the monorepo's -- that is what the nRF
# actually compiles, so a divergence between the two would show up here.
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

params=sphincs-sha2-128s

echo "== compiling pq_sig_test =="
# -w: the reference sphincsplus and MCUboot's FIH headers are noisy, and this
# harness is not where we police their warnings.
# --gc-sections: drops the curve25519 / rand paths ed25519-donna references but
# this harness never calls.
gcc -O2 -w \
    -DPQ_HOST_TEST -DPARAMS="$params" \
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
