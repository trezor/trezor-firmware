#!/usr/bin/env python3
"""Generate a multi-variant, manifest-based firmware_root cross-validation vector.

Builds SYNTHETIC firmware images for several variants -- each image is
[manifest | secmon code | kernel code], where the variant leaf is
H(0x00 || manifest) and the manifest references each module directly by
code_hash = SHA-256 over the whole module code (one commitment hop, no per-module
header). Computes the founder firmware_root + per-variant proofs
(firmware_module.build_founder_tree), self-checks the fold in Python, and writes
a vector the C harness (crossvalidate.c) replays through the REAL device math
(firmware_verify_manifest).

Image layout (offsets authenticated via the manifest's addr fields):
  0x000  manifest      (padded to MANIFEST_REGION)
  MR     secmon code   (padded to CODE_ALIGNMENT)
  ...    kernel code   (padded to CODE_ALIGNMENT)

FWM2 layout (little-endian):
  "FWM2" | founder_root(32) | variant_count(u32)
  per variant:
    variant_id(u32)
    image_len(u32) | image[image_len]
    manifest_len(u32)
    alt_len(u32) | alt_image[alt_len]   (custom only -- a DIFFERENT-size/version
                                         app that must fold to the SAME slot; 0
                                         for official variants)
    proof_count(u32) | proof_node(32) * proof_count
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from trezor_core_tools import firmware_module as fm  # noqa: E402

MANIFEST_REGION = 0x400  # reserved region for the manifest at image start
CODE_ALIGNMENT = 0x400
CODE_SIZE = 0x100

# Includes the CUSTOM variant (1): its manifest carries a REAL app code_hash
# (the creator's), but variant_leaf zeroes it for the founder tree -- so the
# device must accept any app under this slot (integrity-only), while an official
# variant's app is founder-bound. crossvalidate.c exercises both.
VARIANTS = {1: "custom", 2: "universal", 3: "bitcoin-only", 4: "prodtest"}


def _align(x: int) -> int:
    return (x + CODE_ALIGNMENT - 1) // CODE_ALIGNMENT * CODE_ALIGNMENT


def _build_variant_image(
    vid: int,
    version: bytes = b"\x01\x00\x00\x00",
    app_size: int = CODE_SIZE,
    app_byte: int | None = None,
):
    """Lay out [manifest | secmon code | kernel code] and return
    (image, manifest_bytes). Each manifest entry commits its module directly by
    code_hash = SHA-256 over the module code (no per-module header). The secmon is
    fixed (founder-bound); the app version/size/code vary per (custom) build."""
    secmon_code = b"\xaa" * CODE_SIZE
    kernel_code = bytes([vid & 0xFF if app_byte is None else app_byte]) * app_size

    # Module code offsets. The app addr depends ONLY on the (fixed) secmon size,
    # so it is stable across app sizes -- the founder commits it even for custom.
    sec_addr = MANIFEST_REGION
    ker_addr = _align(sec_addr + CODE_SIZE)

    entries = [
        # secmon is the secure boot/entry module (FLAG_BOOT).
        {
            "module_type": 1,
            "flags": fm.FW_MANIFEST_ENTRY_FLAG_BOOT,
            "addr": sec_addr,
            "size": CODE_SIZE,
            "code_hash": hashlib.sha256(secmon_code).digest(),
        },
        {
            "module_type": 2,
            "flags": 0,
            "addr": ker_addr,
            "size": app_size,
            "code_hash": hashlib.sha256(kernel_code).digest(),
        },
    ]
    manifest = fm.build_manifest(vid, entries, firmware_version=version)

    image = bytearray(b"\xff" * _align(ker_addr + app_size))
    image[0 : len(manifest)] = manifest
    image[sec_addr : sec_addr + CODE_SIZE] = secmon_code
    image[ker_addr : ker_addr + app_size] = kernel_code
    return bytes(image), manifest


def build():
    images, manifests, leaves, alts = {}, {}, {}, {}
    for vid, vname in VARIANTS.items():
        if vid == fm.FW_VARIANT_CUSTOM:
            # Custom slot: the founder leaf zeroes the app version/size/code_hash,
            # so any creator app folds to it. Prove it -- build the primary and an
            # ALT with a DIFFERENT app version + size + code, and assert identical
            # leaves. The alt is replayed on-device (crossvalidate) too.
            image, manifest = _build_variant_image(
                vid, version=b"\x02\x01\x00\x00", app_size=CODE_SIZE
            )
            alt_image, alt_manifest = _build_variant_image(
                vid, version=b"\x09\x09\x09\x09", app_size=CODE_SIZE * 2, app_byte=0x5A
            )
            assert fm.variant_leaf(manifest) == fm.variant_leaf(
                alt_manifest
            ), "custom leaf is not app-agnostic (version/size/code_hash not zeroed?)"
            alts[vid] = alt_image
        else:
            image, manifest = _build_variant_image(vid)
            alts[vid] = b""
        images[vid] = image
        manifests[vid] = manifest
        leaves[vid] = fm.variant_leaf(manifest)
    root, proofs = fm.build_founder_tree(list(leaves.values()))  # asserts folds
    return images, manifests, leaves, proofs, root, alts


def emit(path: Path) -> None:
    images, manifests, leaves, proofs, root, alts = build()

    print(f"founder firmware_root : {root.hex()}")
    buf = b"FWM2" + root + struct.pack("<I", len(images))
    for vid, vname in VARIANTS.items():
        image, manifest, alt = images[vid], manifests[vid], alts[vid]
        proof = proofs[leaves[vid]]
        alt_note = f" +alt {len(alt)}B" if alt else ""
        print(
            f"  variant {vid:>2} ({vname:<12}) image {len(image)}B "
            f"manifest {len(manifest)}B leaf {leaves[vid].hex()[:12]} "
            f"proof {len(proof)}{alt_note}"
        )
        buf += struct.pack("<I", vid)
        buf += struct.pack("<I", len(image)) + image
        buf += struct.pack("<I", len(manifest))
        buf += struct.pack("<I", len(alt)) + alt
        buf += struct.pack("<I", len(proof))
        for node in proof:
            buf += node

    path.write_bytes(buf)
    print(f"wrote {path} ({len(buf)} bytes)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("multivariant.vec")
    emit(out)
