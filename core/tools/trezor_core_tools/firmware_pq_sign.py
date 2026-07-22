#!/usr/bin/env python3
"""Sign a Merkle-tree firmware: fold the founder firmware_root into the bootloader.

Each firmware.bin (built with `pq_secure_boot`) starts with a manifest ("firmware
directory") whose hash is that variant's leaf: variant_leaf = H(0x00 || manifest).
The founder firmware_root is the Merkle tree over the variant leaves of ALL
variants. This tool:

  1. reads each variant's manifest and computes its variant leaf,
  2. builds the founder firmware_root over those leaves (a single leaf when only
     one variant is given -> firmware_root == that leaf),
  3. folds firmware_root into the (one, variant-agnostic) bootloader header and
     re-signs it (dev keys),
  4. bakes each variant's Merkle proof (the co-path variant_leaf -> firmware_root)
     into its firmware.bin, in the manifest region right after the manifest, so
     the image is self-contained (empty for a single variant). Both the device at
     boot and the OTA fold the variant leaf through the embedded proof to
     firmware_root -- no proof is stored in the boot header.

Pass `--firmware` once per variant (e.g. universal + bitcoin-only + prodtest).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trezor_core_tools import firmware_module

from trezorlib._internal import firmware_headers


def _variant_info(firmware: Path) -> dict:
    fw = firmware.read_bytes()
    entries = firmware_module.manifest_entries(fw)
    if not entries:
        raise SystemExit(f"{firmware}: no manifest modules found")
    # Every entry (incl. a CUSTOM variant's kernel+coreapp) carries a REAL
    # code_hash on flash after the build fill; a zero hash means the manifest was
    # never code-filled. (The custom app's founder-zeroing happens only in the
    # authenticity leaf, computed by variant_leaf -- never on flash.)
    unfilled = [e for e in entries if e["size"] > 0 and not any(e["code_hash"])]
    if unfilled:
        raise SystemExit(
            f"{firmware}: manifest code hashes not filled (run the firmware "
            "build / headertool_pq first)"
        )
    manifest = firmware_module.read_manifest(fw)
    return {
        "path": firmware,
        "fw": fw,
        "entries": entries,
        "manifest": manifest,
        "leaf": firmware_module.variant_leaf(manifest),
        "variant": firmware_module.manifest_variant(manifest),
    }


def sign_firmware_images(
    firmwares: list[Path], bootloader: Path
) -> tuple[list[dict], bytes, firmware_headers.BootloaderV2Image]:
    """Compute the founder firmware_root over all variants, sign the bootloader,
    and attach each variant's proof. Returns (variants, firmware_root, bl)."""
    variants = [_variant_info(f) for f in firmwares]
    leaves = [v["leaf"] for v in variants]

    if len(leaves) == 1:
        firmware_root = leaves[0]
        proofs = {leaves[0]: []}
    else:
        firmware_root, proofs = firmware_module.build_founder_tree(leaves)
    for v in variants:
        v["proof"] = proofs[v["leaf"]]
        # Bake the proof into the image's manifest region (right after the
        # manifest, OUTSIDE the leaf) so firmware.bin is self-contained. This does
        # not change the manifest/leaf -- the proof is excluded from the leaf.
        fw_ba = bytearray(v["fw"])
        firmware_module.install_manifest_proof(fw_ba, v["proof"])
        v["path"].write_bytes(fw_ba)
        v["fw"] = bytes(fw_ba)

    # Fold firmware_root into the bootloader header's firmware_root and re-sign.
    bl = firmware_headers.BootloaderV2Image.parse(bootloader.read_bytes())
    bl.header.firmware_root = firmware_root
    bl.sign_with_devkeys()
    bootloader.write_bytes(bl.build())

    return variants, firmware_root, bl


def _short(b: bytes) -> str:
    return b[:6].hex()


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--firmware",
        type=Path,
        action="append",
        required=True,
        help="firmware.bin (header-filled); repeat once per variant",
    )
    ap.add_argument(
        "--bootloader",
        type=Path,
        required=True,
        help="bootloader.bin (re-signed in place)",
    )
    ap.add_argument("--manifest-out", type=Path)
    ap.add_argument(
        "--vector-out", type=Path, help="write the first variant's raw manifest bytes"
    )
    ap.add_argument(
        "--install-proof",
        type=Path,
        help="stamp THIS variant's firmware_type into the bootloader for "
        "direct-flashing that variant (no OTA); the proof rides in the image",
    )
    ap.add_argument(
        "--bare",
        action="store_true",
        help="leave the bootloader firmware_type BARE (0) so the firmware "
        "must be installed via OTA; zeroed explicitly so re-signing a "
        "stamped bootloader is bare too",
    )
    args = ap.parse_args()

    if args.install_proof and args.bare:
        raise SystemExit("--bare and --install-proof are mutually exclusive")

    variants, firmware_root, bl = sign_firmware_images(args.firmware, args.bootloader)

    single = len(variants) == 1
    print(
        f"firmware_root  : {firmware_root.hex()}"
        + ("  (single variant)" if single else f"  (founder over {len(variants)})")
    )
    for v in variants:
        leaf, proof = v["leaf"], v["proof"]
        print(
            f"  {v['path'].name:24} leaf {_short(leaf)}  proof {len(proof)} node(s)"
            f" baked into image"
        )
        # Sanity: this variant's leaf + proof must fold to firmware_root, and the
        # proof just baked into the image must read back identically.
        assert firmware_module._fold_proof(leaf, proof) == firmware_root
        assert firmware_module.read_manifest_proof(v["fw"]) == proof

    # For a direct flash (no OTA) the proof already rides in the firmware image;
    # we only stamp the variant into the bootloader's firmware_type so the device
    # reads as PROVISIONED (fw_check keys off firmware_type != 0) and picks the
    # right storage domain. firmware_type is unauth, so this does not re-sign.
    if args.install_proof:
        match = next((v for v in variants if v["path"] == args.install_proof), None)
        if match is None:
            raise SystemExit(
                f"--install-proof {args.install_proof}: not among --firmware"
            )
        # Dev builds are official, so firmware_type == variant (no custom flag).
        bl.unauth.firmware_type = match["variant"]
        args.bootloader.write_bytes(bl.build())
        print(
            f"stamped firmware_type={match['variant']} ({match['path'].name}) into "
            "the bootloader for direct-flashing (the proof rides in the image)"
        )
    elif args.bare:
        # firmware_type 0 -> the device reads as unprovisioned and MUST receive the
        # firmware via OTA (phase 1 stamps firmware_type; the proof rides in the
        # image). Zero explicitly so re-signing a stamped bootloader ends up bare.
        bl.unauth.firmware_type = 0
        args.bootloader.write_bytes(bl.build())
        print("bootloader firmware_type left BARE (0) -> install via OTA")

    print(
        f"bootloader     : signed root {bl.merkle_root().hex()[:12]}, "
        f"header firmware_root {bytes(bl.header.firmware_root).hex()[:12]}"
    )

    if args.vector_out:
        args.vector_out.write_bytes(variants[0]["manifest"])
    if args.manifest_out:
        args.manifest_out.write_text(
            json.dumps(
                {
                    "firmware_root": firmware_root.hex(),
                    "variants": [
                        {
                            "firmware": v["path"].name,
                            "leaf": v["leaf"].hex(),
                            "proof": [n.hex() for n in v["proof"]],
                        }
                        for v in variants
                    ],
                    "bootloader_signed_root": bl.merkle_root().hex(),
                },
                indent=2,
            )
        )

    print("\nverification:")
    try:
        bl.verify(dev_keys=True)
        print("  bootloader signature (covers firmware_root)  OK")
    except Exception as e:  # noqa: BLE001
        print(f"  bootloader signature FAILED: {e}")
    assert bytes(bl.header.firmware_root) == firmware_root
    print("  every variant leaf folds to firmware_root  OK")


if __name__ == "__main__":
    main()
