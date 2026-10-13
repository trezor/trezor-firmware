#!/usr/bin/env python3
"""Check a PQ-native nRF image the way its MCUboot will (image_pq.c), on the host.

Verifies image hash, leaf, fold to modelRoot and the Ed25519 half of the hybrid
signature (SLH-DSA is not checked), and reports which founder pool it verifies
under. Usage: nrf_pq_check.py <signed-nrf-image.bin>
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from trezor_core_tools import nrf_tree
from trezorlib import _ed25519
from trezorlib.firmware.models import ROOT_ED25519_KEYS, ROOT_ED25519_KEYS_DEV

# From trezorlib (what the signer uses), not a copy. Devel has 2 keys, production 3.
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
        "(leaf = H(0x00 || the role-bound slot over that hash))"
    )

    # MCUboot rejects on its own hash check before founder verification.
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

    # Protected area only, as the device reads it (nrf_image_find_prot_tlv).
    sigmask = nrf_tree.mcuboot_find_prot_tlv(image, nrf_tree.TLV_SIGMASK)
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
    slh_sigs = [x for x in slh if x is not None]
    ec_sigs = [x for x in ec if x is not None]

    matched_pool = None
    for pool_name, pool in (
        ("DEVEL", DEVEL_EC_KEYS),
        ("PRODUCTION", PRODUCTION_EC_KEYS),
    ):
        found = []
        for slot in range(2):
            digest = hashlib.sha256(root + slh_sigs[slot]).digest()
            hit = None
            for idx, pk in enumerate(pool):
                try:
                    _ed25519.checkvalid(ec_sigs[slot], digest, pk)
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
    # The sigmask must name exactly the keys that verified, in slot order.
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
