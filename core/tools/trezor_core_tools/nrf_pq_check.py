#!/usr/bin/env python3
"""Check a PQ-native nRF image the way the nRF's MCUboot will, on the host.

Replays what image_pq.c:pq_image_verify() does -- image hash, leaf, fold to
modelRoot, and the Ed25519 half of the hybrid signature -- and reports WHICH
founder key pool the image verifies under (devel or production).

Why this exists: a key-pool mismatch produces a perfectly well-formed image that
simply will not boot, and the only symptom on device is a silent verification
failure. Finding that by flashing costs a full build+flash cycle each time; this
answers it in a second, and says explicitly which side is wrong.

The SLH-DSA half is NOT checked (no host SLH-DSA in this environment). That is fine
for the question this tool answers: the Ed25519 half signs SHA256(modelRoot ||
slh_signature), so it already pins the modelRoot, the PQ signature bytes and the key
identity -- if it verifies, the pool and the message construction are right.

Usage:
    nrf_pq_check.py <signed-nrf-image.bin>
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from trezor_core_tools import nrf_tree

from trezorlib import _ed25519
from trezorlib.firmware.models import ROOT_ED25519_KEYS, ROOT_ED25519_KEYS_DEV

# Taken from trezorlib, which is what the signer uses -- not copied. A local copy
# here could disagree with the keys an image was actually signed with, which would
# make this checker confidently wrong about the very thing it exists to catch. The
# DEVEL pool has two keys, production three.
DEVEL_EC_KEYS = ROOT_ED25519_KEYS_DEV
PRODUCTION_EC_KEYS = ROOT_ED25519_KEYS


def _fold(leaf: bytes, nodes: list[bytes]) -> bytes:
    node = leaf
    for sib in nodes:
        node = hashlib.sha256(b"\x01" + min(node, sib) + max(node, sib)).digest()
    return node


def check(image: bytes) -> int:
    problems = 0

    if not nrf_tree.has_pq_material(image):
        print(f"NOT PQ-NATIVE: no founder TLVs in {len(image)} B.")
        print("  -> built without --nrf-pq-native, or the bare build output.")
        return 1
    prot_end = nrf_tree.mcuboot_prot_end(image)
    print(
        f"image {len(image)} B; hashed range {prot_end} B "
        f"(leaf = H(0x00 || that hash))"
    )

    # MCUboot's own hash must match the protected region, or it rejects the image
    # before founder verification is even reached.
    want = nrf_tree.mcuboot_image_hash(image)
    got = nrf_tree.mcuboot_find_tlv(image, nrf_tree.MCUBOOT_TLV_SHA256)
    if got != want:
        print(
            f"  FAIL image-hash TLV {got.hex()[:16] if got else None} != "
            f"computed {want.hex()[:16]} (protected area edited without re-stamping?)"
        )
        problems += 1
    else:
        print(f"  image-hash TLV consistent ({want.hex()[:16]}...)")

    sigmask = nrf_tree.mcuboot_find_tlv(image, nrf_tree.TLV_SIGMASK)
    if sigmask is None or len(sigmask) != 1:
        print("  FAIL no protected sigmask TLV")
        return problems + 1
    mask = sigmask[0]
    named = [i for i in range(8) if mask & (1 << i)]
    print(f"  sigmask 0x{mask:02x} -> names key(s) {named}")

    try:
        model = nrf_tree.mcuboot_model_id(image)
        print(f"  model id {model!r}")
    except ValueError as e:
        print(f"  FAIL {e}")
        problems += 1

    co = nrf_tree.mcuboot_find_tlv(image, nrf_tree.PQ_TLV_MERKLE_PROOF)
    if not co or len(co) % 32:
        print("  FAIL missing/malformed co-path TLV")
        return problems + 1
    root = _fold(
        nrf_tree.nrf_leaf(image), [co[i : i + 32] for i in range(0, len(co), 32)]
    )
    print(f"  folded modelRoot {root.hex()[:16]}... ({len(co) // 32}-node co-path)")

    slh = [
        nrf_tree.mcuboot_find_tlv(image, t)
        for t in (nrf_tree.PQ_TLV_SLH_SIG_0, nrf_tree.PQ_TLV_SLH_SIG_1)
    ]
    ec = [
        nrf_tree.mcuboot_find_tlv(image, t)
        for t in (nrf_tree.PQ_TLV_EC_SIG_0, nrf_tree.PQ_TLV_EC_SIG_1)
    ]
    if any(x is None for x in slh + ec):
        print("  FAIL missing founder signature TLV(s)")
        return problems + 1

    matched_pool = None
    for pool_name, pool in (
        ("DEVEL", DEVEL_EC_KEYS),
        ("PRODUCTION", PRODUCTION_EC_KEYS),
    ):
        found = []
        for slot in range(2):
            digest = hashlib.sha256(root + slh[slot]).digest()
            hit = None
            for idx, pk in enumerate(pool):
                try:
                    _ed25519.checkvalid(ec[slot], digest, pk)
                    hit = idx
                    break
                except Exception:  # noqa: BLE001  (any failure = not this key)
                    pass
            found.append(hit)
        ok = all(h is not None for h in found) and found[0] != found[1]
        print(
            f"  {pool_name:<10} pool: slot0 -> key {found[0]}, slot1 -> key {found[1]}"
            f"  {'VERIFIES' if ok else 'no'}"
        )
        if ok:
            matched_pool = (pool_name, found)

    if matched_pool is None:
        print(
            "\nRESULT: signatures verify under NO known founder pool -- the signer used"
            " keys neither bootloader knows."
        )
        return problems + 1

    pool_name, found = matched_pool
    # The bootloader indexes keys by the sigmask, so the mask must name exactly the
    # keys that actually verified, in slot order.
    if found != named:
        print(
            f"\nRESULT: verifies under {pool_name}, but the sigmask names {named} while"
            f" the signatures are from {found} -- the nRF maps slot i to the i-th"
            " lowest set bit, so it would check the wrong keys."
        )
        return problems + 1

    print(
        f"\nRESULT: OK -- verifies under the {pool_name} founder pool, sigmask agrees."
    )
    print(
        f"  Build MCUboot to match: {'CONFIG_BOOT_PRODUCTION_KEY=y' if pool_name == 'PRODUCTION' else 'CONFIG_BOOT_PRODUCTION_KEY=n (default)'}"
    )
    return problems


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(1 if check(Path(sys.argv[1]).read_bytes()) else 0)


if __name__ == "__main__":
    main()
