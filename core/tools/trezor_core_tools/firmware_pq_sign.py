#!/usr/bin/env python3
"""Sign a Merkle-tree firmware: fold the founder firmware_root into the bootloader.

Computes each variant's leaf, builds firmware_root over them, folds it into the
bootloader header, re-signs (dev keys) and bakes each variant's proof into its
image. Pass `--firmware` once per variant. See docs/core/build/xtask.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trezor_core_tools import bootloader_provenance, firmware_module, nrf_tree
from trezorlib._internal import firmware_headers

# MCUboot IMAGE_TLV_SHA256: the update-required hint (not a trust input).
MCUBOOT_TLV_SHA256 = 0x10

# Default key-slot selection; matches BootloaderV2Image.sign_with_devkeys.
# sigmask is authenticated, so it is fixed before any leaf is computed.
DEV_SIGMASK = (1 << 0) | (1 << 1)

# Device rules (boot_header.c): exactly SIGNATURE_COUNT slots named, all used.
SIGNATURE_COUNT = 2  # BOOT_HEADER_SIGNATURE_COUNT
MAX_KEY_SLOTS = 3  # _Static_assert(ARRAY_LENGTH(BOARDLOADER_PQ_KEYS) <= 3)


def _check_sigmask(mask: int, signing_inline: bool) -> None:
    if not 0 <= mask <= 0xFF:
        raise SystemExit(f"sigmask 0x{mask:x} does not fit the header's uint8_t")
    slots = [i for i in range(8) if mask & (1 << i)]
    if len(slots) != SIGNATURE_COUNT:
        raise SystemExit(
            f"sigmask 0x{mask:02x} names {len(slots)} key slot(s), but the header "
            f"carries exactly {SIGNATURE_COUNT} signatures and the device requires "
            f"every named slot to be used -- name exactly {SIGNATURE_COUNT}"
        )
    if slots[-1] >= MAX_KEY_SLOTS:
        raise SystemExit(
            f"sigmask 0x{mask:02x} names slot {slots[-1]}, but only "
            f"{MAX_KEY_SLOTS} founder key slots exist (0..{MAX_KEY_SLOTS - 1})"
        )
    if signing_inline and mask != DEV_SIGMASK:
        # sign_with_devkeys writes the development selection itself.
        raise SystemExit(
            f"sigmask 0x{mask:02x} cannot be signed inline: inline signing uses "
            f"the development keys, which are slots 0x{DEV_SIGMASK:02x}. Prepare "
            "with --unsigned and let the ceremony sign for any other selection"
        )


def _variant_info(firmware: Path) -> dict:
    fw = bytearray(firmware.read_bytes())
    if not firmware_module.manifest_entries(fw):
        raise SystemExit(f"{firmware}: no manifest modules found")
    # The build emits a template with zero code_hashes; fill them here.
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


def _authenticity_manifest_field(variant: dict) -> dict:
    """The CUSTOM variant's authenticity manifest (what presigned_check folds);
    only CUSTOM's leaf is code-independent, so only it gets one."""
    if variant["variant"] != firmware_module.FW_VARIANT_SEC_CUSTOM:
        return {}
    return {
        "authenticity_manifest": firmware_module.authenticity_manifest(
            variant["manifest"]
        ).hex()
    }


def sign_firmware_images(
    firmwares: list[Path],
    bootloader: Path,
    nrf: Path | None = None,
    nrf_pq_native: bool = False,
    sign: bool = True,
    sigmask: int = DEV_SIGMASK,
) -> tuple[list[dict], bytes, firmware_headers.BootloaderV2Image, dict | None]:
    """Fill manifests, build firmware_root, sign the bootloader, bake proofs.

    Returns (variants, firmware_root, bl, nrf_info). Without `nrf` the model path
    is empty (modelRoot == model leaf); with it the nRF image is a peer leaf under
    the one boot-header signature and nrf_info carries the FirmwareBegin fields.
    """
    variants = [_variant_info(f) for f in firmwares]
    leaves = [v["leaf"] for v in variants]

    if len(leaves) == 1:
        firmware_root = leaves[0]
        proofs = {leaves[0]: []}
    else:
        firmware_root, proofs = firmware_module.build_founder_tree(leaves)
    for v in variants:
        v["proof"] = proofs[v["leaf"]]
        # The proof sits outside the leaf, so baking it in does not move the leaf.
        fw_ba = bytearray(v["fw"])
        firmware_module.install_manifest_proof(fw_ba, v["proof"])
        v["path"].write_bytes(fw_ba)
        v["fw"] = bytes(fw_ba)

    # firmware_root is authenticated: set it before the leaf is read.
    bl = firmware_headers.BootloaderV2Image.parse(bootloader.read_bytes())
    # Drop any stale signature; setting firmware_root changes the digest.
    for idx in range(len(bl.unauth.slh_signatures)):
        bl.unauth.slh_signatures[idx] = b"\x00" * len(bl.unauth.slh_signatures[idx])
    for idx in range(len(bl.unauth.ec_signatures)):
        bl.unauth.ec_signatures[idx] = b"\x00" * len(bl.unauth.ec_signatures[idx])
    bl.header.firmware_root = firmware_root
    # sigmask is authenticated: set it before anything is hashed.
    _check_sigmask(sigmask, signing_inline=sign)
    bl.header.sigmask = sigmask

    nrf_info: dict | None = None
    if nrf is None:
        # Empty model path: modelRoot == model leaf.
        if sign:
            bl.sign_with_devkeys()
    else:
        nrf_image = nrf.read_bytes()
        if nrf_pq_native:
            # Protected TLVs are inside the leaf: stamp sigmask and monotonic
            # (one anti-rollback axis with the STM) before the tree is built.
            nrf_sigmask = bl.header.sigmask
            nrf_image = nrf_tree.set_protected_sigmask(nrf_image, nrf_sigmask)
            nrf_monotonic = bl.header.monotonic
            nrf_image = nrf_tree.set_protected_monotonic(nrf_image, nrf_monotonic)
            # Founder record SIZES are inside the leaf; values come after signing.
            nrf_image = nrf_tree.add_pq_placeholders(nrf_image)
        model_val = nrf_tree.model_leaf_value(bl)  # sizes model path -> stable leaf
        # The nRF slot wraps MCUboot's image hash, not the whole image.
        model_root, model_proofs = nrf_tree.build_model_tree(
            [model_val, nrf_tree.nrf_leaf_value(nrf_image)]
        )
        nrf_tree.place_bootloader_in_tree(bl, model_proofs[0])  # co-path, no sign
        assert bl.merkle_root() == model_root, "boot-header fold != modelRoot"
        if sign:
            bl.sign_with_devkeys()

        if nrf_pq_native and sign:
            # The nRF embeds the same signature bytes as the boot header. The
            # stamped protected values must still match, or the nRF rejects at boot.
            if bl.header.monotonic != nrf_monotonic:
                raise SystemExit(
                    f"monotonic_version changed during signing (stamped "
                    f"{nrf_monotonic}, header now {bl.header.monotonic}); the "
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
        if nrf_pq_native:
            # Written even if unsigned: the recorded hash describes the placeholder
            # image. Re-pad to 16 for the OTA engine (outside the leaf).
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


def finalize_bare_bootloader(
    bl: firmware_headers.BootloaderV2Image, bootloader: Path
) -> tuple[int, int]:
    """Leave firmware_type BARE (NONE) and return (offset, bare_value).

    NONE = 0xCCCCCCCC is "unprovisioned", distinct from INVALID = 0 (erased
    memory must not decode into it). The field is unauthenticated, so the
    installer stamps it later without a key. Located by probe: flip, diff.
    """
    bare_value = firmware_module.FW_VARIANT_SEC_NONE
    bl.unauth.firmware_type = bare_value
    bare = bl.build()
    # Complement, so all four bytes differ whatever the codeword.
    bl.unauth.firmware_type = bare_value ^ 0xFFFFFFFF
    probe = bl.build()
    bl.unauth.firmware_type = bare_value
    differing = [i for i in range(len(bare)) if bare[i] != probe[i]]
    if len(differing) != 4 or differing != list(range(differing[0], differing[0] + 4)):
        raise SystemExit(
            f"firmware_type is not 4 contiguous bytes of the built header "
            f"({len(differing)} bytes differ) -- the probe cannot locate it"
        )
    firmware_type_offset = differing[0]
    bootloader.write_bytes(bare)
    print(
        f"bootloader firmware_type left BARE (NONE) at offset "
        f"{firmware_type_offset}, 4 bytes"
        " -> stamped by whoever installs it"
    )
    return firmware_type_offset, bare_value


def build_bundle(
    variants: list[dict],
    firmware_root: bytes,
    bl: firmware_headers.BootloaderV2Image,
    nrf_info: dict | None,
    firmware_type_offset: int,
    bare_value: int,
    bootloader: Path,
) -> dict:
    """The release container (see firmware_module.CONTAINER_MAGIC).

    Every field is read back from the artifacts, never an independent claim.
    """
    bundle = {
        "format": firmware_module.CONTAINER_MAGIC,
        "format_version": firmware_module.CONTAINER_VERSION,
        # From the signed boot header, not from a flag.
        "model": firmware_module.boot_header_model_id(bl.header),
        "firmware_root": firmware_root.hex(),
        "bootloader": {
            "file": bootloader.name,
            "signed_root": bl.merkle_root().hex(),
            # sigmask: authenticated in the header; attach refuses a mismatch.
            "sigmask": bl.header.sigmask,
            # Code digest + founder pool: what a ceremony pins; the pool is a
            # compile-time choice (BOOTLOADER_DEVEL) the header does not record.
            "code_sha256": bootloader_provenance.code_digest(
                bootloader.read_bytes()
            ),
            "founder_pool": bootloader_provenance.detect_pool(
                bootloader.read_bytes()
            ),
            # Where firmware_type sits, so a stamping tool needs no layout knowledge.
            "firmware_type": {
                "offset": firmware_type_offset,
                "len": 4,
                "bare": bare_value,
            },
        },
        "variants": [
            {
                # Name from the folded codeword, not the filename.
                "variant": firmware_module.FW_VARIANT_NAME[v["variant"]],
                "file": v["path"].name,
                "leaf": v["leaf"].hex(),
                "proof": [n.hex() for n in v["proof"]],
                # What firmware_type must hold to boot this variant.
                "firmware_type": v["variant"],
                **_authenticity_manifest_field(v),
            }
            for v in variants
        ],
        # Routing only: each entry names its (kind, index) slot; verifiers take
        # kind/index from their own build config.
        "coprocessors": [],
    }
    if nrf_info is not None:
        # FirmwareBegin inputs: nrf_co_path / nrf_length / nrf_image_hash.
        bundle["coprocessors"].append(
            {
                "kind": "nrf",
                "index": 0,
                "file": nrf_info["image_name"],
                # From the image's own TLV; cross-checks the top-level `model`.
                "image_model_id": nrf_info["model_id"].decode(errors="replace"),
                "length": nrf_info["length"],
                "image_hash": nrf_info["image_hash"].hex(),
                "co_path": [n.hex() for n in nrf_info["co_path"]],
                "model_root": nrf_info["model_root"].hex(),
            }
        )
    return bundle


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
    ap.add_argument(
        "--unsigned",
        action="store_true",
        help="PREPARE only: fold everything and leave the signature region "
        "zero, so the release can be signed as a whole afterwards (the order a "
        "founder ceremony runs in). The container records the modelRoot to be "
        "signed, so it IS the signing request.",
    )
    ap.add_argument(
        "--sigmask",
        type=lambda s: int(s, 0),
        default=DEV_SIGMASK,
        help="which key slots sign this release, as a bitmask (e.g. 0x03 for slots "
        "0 and 1). AUTHENTICATED -- it is inside the digest, so it is committed "
        "while the release is PREPARED, before any leaf exists and before anyone "
        "holds a key. A founder ceremony signing with a different selection must "
        f"say so here; the default 0x{DEV_SIGMASK:02x} is the development one.",
    )
    ap.add_argument("--manifest-out", type=Path)
    ap.add_argument(
        "--vector-out", type=Path, help="write the first variant's raw manifest bytes"
    )
    args = ap.parse_args()

    variants, firmware_root, bl, nrf_info = sign_firmware_images(
        args.firmware,
        args.bootloader,
        args.nrf,
        args.nrf_pq_native,
        sign=not args.unsigned,
        sigmask=args.sigmask,
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
        # Leaf + proof must fold to firmware_root; the baked proof must read back.
        assert firmware_module._fold_proof(leaf, proof) == firmware_root
        assert firmware_module.read_manifest_proof(v["fw"]) == proof

    if nrf_info is not None:
        # Mirrors the device install check: nRF leaf + co-path == signed modelRoot.
        assert nrf_info["model_root"] == bytes(bl.merkle_root())
        print(
            f"nRF leaf        : {nrf_info['image_name']} "
            f"model_id={nrf_info['model_id'].decode(errors='replace')} "
            f"{nrf_info['length']} B, co-path {len(nrf_info['co_path'])} node(s)"
        )
        print("  committed under the ONE boot-header signature (modelRoot leaf)")

    firmware_type_offset, bare_value = finalize_bare_bootloader(bl, args.bootloader)

    print(
        f"bootloader     : signed root {bl.merkle_root().hex()[:12]}, "
        f"header firmware_root {bytes(bl.header.firmware_root).hex()[:12]}"
    )

    if args.vector_out:
        args.vector_out.write_bytes(variants[0]["manifest"])
    if args.manifest_out:
        args.manifest_out.write_text(
            json.dumps(
                build_bundle(
                    variants,
                    firmware_root,
                    bl,
                    nrf_info,
                    firmware_type_offset,
                    bare_value,
                    args.bootloader,
                ),
                indent=2,
            )
            + "\n"
        )

    print("\nverification:")
    if args.unsigned:
        # The signature region is deliberately zero; only the input is checkable.
        assert not bl.signature_present(), "an unsigned release carries no signature"
        print(f"  UNSIGNED -- modelRoot to sign: {bl.merkle_root().hex()}")
        print(f"  sigmask committed            : 0x{bl.header.sigmask:02x}")
    else:
        try:
            bl.verify(dev_keys=True)
            print("  bootloader signature (covers firmware_root)  OK")
        except Exception as e:  # noqa: BLE001
            print(f"  bootloader signature FAILED: {e}")
    assert bytes(bl.header.firmware_root) == firmware_root
    print("  every variant leaf folds to firmware_root  OK")


if __name__ == "__main__":
    main()
