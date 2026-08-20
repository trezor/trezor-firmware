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

from trezor_core_tools import firmware_module, nrf_tree

from trezorlib._internal import firmware_headers

# MCUboot IMAGE_TLV_SHA256 -- the image hash the nRF's MCUboot computes and that
# nrf_get_info() reports (io/nrf/stm32u5/nrf_update.c). This is the value the
# device compares against FirmwareBegin.nrf_image_hash to decide "update
# required"; it is NOT a trust input (authenticity is the co-path fold).
MCUBOOT_TLV_SHA256 = 0x10


def _variant_info(firmware: Path) -> dict:
    fw = bytearray(firmware.read_bytes())
    if not firmware_module.manifest_entries(fw):
        raise SystemExit(f"{firmware}: no manifest modules found")
    # Fill-at-sign: the build emits a manifest TEMPLATE (module_type/addr/size +
    # variant + chunk_size) with code_hashes left ZERO. We compute the real
    # smart-hashing chain hashes here -- over the placed code, at the template's
    # chunk_size (FW_CHUNK_SIZE, the build-fixed 8K) -- in the SAME step that folds the leaves and
    # signs (so the authenticity data is produced in exactly one place). A CUSTOM
    # variant's kernel+coreapp gets its REAL (integrity) hash here; the
    # founder-zeroing happens only in the authenticity leaf (variant_leaf), never
    # on flash.
    firmware_module.fill_manifest(fw)
    manifest = firmware_module.read_manifest(fw)
    return {
        "path": firmware,
        "fw": bytes(fw),
        "entries": firmware_module.manifest_entries(fw),
        "manifest": manifest,
        "leaf": firmware_module.variant_leaf(manifest),
        "variant": firmware_module.manifest_variant(manifest),
    }


def sign_firmware_images(
    firmwares: list[Path],
    bootloader: Path,
    nrf: Path | None = None,
    nrf_pq_native: bool = False,
) -> tuple[list[dict], bytes, firmware_headers.BootloaderV2Image, dict | None]:
    """Fill each variant's manifest code_hashes (at the template chunk_size),
    compute the founder firmware_root over all variants, sign the bootloader, and
    attach each variant's proof. Returns (variants, firmware_root, bl, nrf_info).

    Without `nrf` the bootloader is signed with an EMPTY model path (modelRoot ==
    model leaf) -- the historical single-leaf signing. With `nrf`, the nRF MCUboot
    image becomes a peer leaf in the model tree: modelRoot = tree(model_leaf,
    nrf_leaf, ..padded); the boot header carries the model co-path for its own
    leaf and is signed over modelRoot -- the ONE signature covers the nRF too. The
    returned nrf_info carries what the OTA client puts in FirmwareBegin (the nRF
    co-path, image length, and the update-required hash); None when no nRF."""
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

    # Fold firmware_root into the bootloader header's firmware_root (authenticated
    # field), THEN sign. The model leaf commits the whole authenticated header, so
    # firmware_root must be set before the leaf is read.
    bl = firmware_headers.BootloaderV2Image.parse(bootloader.read_bytes())
    bl.header.firmware_root = firmware_root

    nrf_info: dict | None = None
    if nrf is None:
        # Single-leaf signing: empty model path, modelRoot == model leaf.
        bl.sign_with_devkeys()
    else:
        # Model-tree signing: nRF image is a peer leaf under modelRoot.
        nrf_image = nrf.read_bytes()
        if nrf_pq_native:
            # PQ-NATIVE: give the image its own copy of the founder material so its
            # MCUboot can verify the tree itself (CONFIG_BOOT_PQ_SECURE_BOOT), instead
            # of trusting the STM's install-time check.
            #
            # Stamp the founder sigmask into the image's PROTECTED TLV first: the
            # signer owns that field exactly as it owns the boot header's sigmask
            # (set value -> compute leaf -> sign), which is what makes it COMMITTED
            # (inside the leaf, so the signature attests to which keys signed) while
            # still costing only a re-sign -- not an nRF rebuild -- on key rotation.
            # Must precede the leaf computation below.
            nrf_sigmask = bl.header.sigmask
            nrf_image = nrf_tree.set_protected_sigmask(nrf_image, nrf_sigmask)
            # Same treatment for the security counter, and for a sharper reason: it
            # must carry the boot header's monotonic_version so the nRF sits on the
            # SAME anti-rollback axis as the STM rather than a second, independent
            # one. Two axes could settle into states neither side rejects -- a
            # forward STM paired with an nRF rolled back over serial recovery.
            # Stamping it HERE, from the header being signed, makes them agree by
            # construction: there is no build-script coordination to get wrong.
            nrf_monotonic = bl.header.monotonic_version
            nrf_image = nrf_tree.set_protected_monotonic(nrf_image, nrf_monotonic)
            # Then the founder records: placeholders now (their SIZES are inside the
            # leaf), values once the signature exists.
            nrf_image = nrf_tree.add_pq_placeholders(nrf_image)
        model_val = nrf_tree.model_leaf_value(bl)  # sizes model path -> stable leaf
        # The nRF slot value is MCUboot's SIGNED REGION, not the whole image (the
        # unprotected TLVs carry signatures -- see nrf_tree.nrf_leaf).
        model_root, model_proofs = nrf_tree.build_model_tree(
            [model_val, nrf_tree.nrf_leaf_value(nrf_image)]
        )
        nrf_tree.sign_bootloader_in_tree(bl, model_proofs[0])  # co-path + sign
        assert bl.merkle_root() == model_root, "boot-header fold != modelRoot"

        if nrf_pq_native:
            # The founder signature over modelRoot covers the nRF leaf too, so the
            # image embeds THE SAME signature bytes the boot header carries -- no
            # separate nRF signing.
            #
            # The sigmask was stamped BEFORE the leaf was computed, using the value
            # the header carried then; signing may set it again. If those ever differ
            # the nRF would carry a mask naming the wrong keys and would reject the
            # image at BOOT -- a late, confusing failure -- so fail here instead.
            if bl.header.monotonic_version != nrf_monotonic:
                raise SystemExit(
                    f"monotonic_version changed during signing (stamped "
                    f"{nrf_monotonic}, header now {bl.header.monotonic_version}); the "
                    "nRF image would enforce a different rollback floor than the STM"
                )
            if bl.header.sigmask != nrf_sigmask:
                raise SystemExit(
                    f"sigmask changed during signing (stamped 0x{nrf_sigmask:02x}, "
                    f"header now 0x{bl.header.sigmask:02x}); the nRF image's "
                    "protected sigmask is inside its leaf, so it must be stamped with "
                    "the final value before the tree is built"
                )
            nrf_image = nrf_tree.fill_pq_material(
                nrf_image,
                list(bl.unauth.slh_signatures),
                list(bl.unauth.ec_signatures),
                model_proofs[1],
            )
            # Re-pad for the OTA engine's flash-aligned size requirement (padding is
            # outside the leaf and past tlv_end, so it affects neither check).
            nrf_image += b"\x00" * ((-len(nrf_image)) % 16)
            nrf.write_bytes(nrf_image)
        image_hash = nrf_tree.mcuboot_find_tlv(nrf_image, MCUBOOT_TLV_SHA256)
        if image_hash is None:
            raise SystemExit(f"{nrf}: nRF MCUboot image has no SHA256 TLV (0x10)")
        nrf_info = {
            "image_name": nrf.name,
            "length": len(nrf_image),  # grown if PQ-native (founder TLVs appended)
            "pq_native": nrf_pq_native,
            "image_hash": image_hash,
            "co_path": model_proofs[1],  # nRF leaf -> modelRoot
            "model_root": model_root,
            "model_id": nrf_tree.mcuboot_model_id(nrf_image),
        }
    bootloader.write_bytes(bl.build())

    return variants, firmware_root, bl, nrf_info


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
        help="firmware.bin (manifest template; code_hashes are filled here); "
        "repeat once per variant",
    )
    ap.add_argument(
        "--bootloader",
        type=Path,
        required=True,
        help="bootloader.bin (re-signed in place)",
    )
    ap.add_argument(
        "--nrf",
        type=Path,
        help="signed nRF MCUboot image (e.g. trezor-ble.bin). If given, it is "
        "committed as a model-tree leaf under the ONE boot-header signature, and "
        "its OTA co-path + hash are written to --manifest-out for the update client.",
    )
    ap.add_argument(
        "--nrf-pq-native",
        action="store_true",
        help="make the nRF image PQ-NATIVE: embed the founder signature + co-path in "
        "its own TLVs so its MCUboot verifies the founder tree itself "
        "(CONFIG_BOOT_PQ_SECURE_BOOT) instead of trusting the STM's install-time "
        "check. Requires an nRF bootloader built with that option, and the image's "
        "protected sigmask TLV must name the signing founder keys.",
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

    variants, firmware_root, bl, nrf_info = sign_firmware_images(
        args.firmware, args.bootloader, args.nrf, args.nrf_pq_native
    )

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

    if nrf_info is not None:
        # The nRF leaf (H(0x00 || image)) folded through its co-path must equal the
        # signed modelRoot (== bl.merkle_root()). Mirrors the device install check.
        assert nrf_info["model_root"] == bytes(bl.merkle_root())
        print(
            f"nRF leaf        : {nrf_info['image_name']} "
            f"model_id={nrf_info['model_id'].decode(errors='replace')} "
            f"{nrf_info['length']} B, co-path {len(nrf_info['co_path'])} node(s)"
        )
        print("  committed under the ONE boot-header signature (modelRoot leaf)")

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
        bundle = {
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
        }
        if nrf_info is not None:
            # What the OTA client feeds to FirmwareBegin (nrf_co_path / nrf_length
            # / nrf_image_hash); model_root is the signed modelRoot for reference.
            bundle["nrf"] = {
                "image": nrf_info["image_name"],
                "model_id": nrf_info["model_id"].decode(errors="replace"),
                "length": nrf_info["length"],
                "image_hash": nrf_info["image_hash"].hex(),
                "co_path": [n.hex() for n in nrf_info["co_path"]],
                "model_root": nrf_info["model_root"].hex(),
            }
        args.manifest_out.write_text(json.dumps(bundle, indent=2))

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
