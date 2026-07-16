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
  4. writes each variant's Merkle proof (the co-path variant_leaf -> firmware_root)
     next to its firmware.bin as `<firmware>.proof` (raw 32-byte nodes; empty for
     a single variant). The OTA delivers that proof; the device folds its variant
     leaf through it to firmware_root.

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
    mods = firmware_module.find_modules(fw)
    if not mods:
        raise SystemExit(f"{firmware}: no TRZM modules found")
    unfilled = [h for h in mods if not any(h["code_hash"]) and h["code_size"] > 0]
    if unfilled:
        raise SystemExit(
            f"{firmware}: module headers not filled (run the firmware build / "
            "headertool_pq first)"
        )
    manifest = firmware_module.read_manifest(fw)
    return {
        "path": firmware,
        "fw": fw,
        "mods": mods,
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
        help="write THIS variant's proof into the bootloader's unauth "
        "region (for direct-flashing that variant, no OTA)",
    )
    ap.add_argument(
        "--bare",
        action="store_true",
        help="leave the bootloader unauth BARE (variant=0, no proof) so "
        "the firmware must be installed via OTA; zeroed explicitly "
        "so re-signing a proof-installed bootloader is bare too",
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
        # Write the per-variant proof next to its firmware.bin.
        proof_path = v["path"].with_suffix(v["path"].suffix + ".proof")
        proof_path.write_bytes(b"".join(proof))
        print(
            f"  {v['path'].name:24} leaf {_short(leaf)}  proof {len(proof)} node(s)"
            f" -> {proof_path.name}"
        )
        # Sanity: this variant's leaf + proof must fold to firmware_root.
        assert firmware_module._fold_proof(leaf, proof) == firmware_root

    # Optionally write one variant's proof into the bootloader unauth so the
    # bootloader + that variant can be direct-flashed (the boot path folds the
    # variant leaf through this proof to firmware_root). The proof is unauth, so
    # this does not affect the signature.
    if args.install_proof:
        match = next((v for v in variants if v["path"] == args.install_proof), None)
        if match is None:
            raise SystemExit(
                f"--install-proof {args.install_proof}: not among --firmware"
            )
        proof = match["proof"]
        MAX = type(bl.unauth).FW_PROOF_MAX_NODES
        if len(proof) > MAX:
            raise SystemExit(f"proof {len(proof)} > {MAX} nodes")
        bl.unauth.firmware_proof_count = len(proof)
        bl.unauth.firmware_proof_nodes = proof + [b"\x00" * 32] * (MAX - len(proof))
        # Also stamp the variant into firmware_type so the direct-flashed device
        # reads as PROVISIONED (fw_check keys off firmware_type != 0). Dev builds
        # are official, so the custom flag (high bit) is 0 -> firmware_type ==
        # variant. (Matches firmware_type_compose(variant, official) on-device.)
        bl.unauth.firmware_type = match["variant"]
        args.bootloader.write_bytes(bl.build())
        print(
            f"installed {match['path'].name} proof ({len(proof)} node(s)) + "
            f"firmware_type={match['variant']} into the bootloader unauth"
        )
    elif args.bare:
        # No variant / no proof in the unauth region, so the device cannot boot a
        # directly-flashed firmware and MUST receive it via OTA (phase 1 writes the
        # variant + proof into the boot header). Zero explicitly so re-signing an
        # already-proof-installed bootloader ends up bare too.
        MAX = type(bl.unauth).FW_PROOF_MAX_NODES
        bl.unauth.firmware_proof_count = 0
        bl.unauth.firmware_proof_nodes = [b"\x00" * 32] * MAX
        bl.unauth.firmware_type = 0
        args.bootloader.write_bytes(bl.build())
        print("bootloader unauth left BARE (variant=0, no proof) -> install via OTA")

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
