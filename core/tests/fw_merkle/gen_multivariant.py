#!/usr/bin/env python3
"""Generate a multi-variant, manifest-based firmware_root cross-validation vector.

Builds SYNTHETIC firmware images for several variants -- each image is
[manifest | secmon module | kernel module], where the variant leaf is
H(0x00 || manifest) and the manifest references each TRZM module header by
header_hash (so per-chunk verification is exercised). Computes the founder
firmware_root + per-variant proofs (firmware_module.build_founder_tree),
self-checks the fold in Python, and writes a vector the C harness
(crossvalidate.c) replays through the REAL device math (firmware_verify_manifest).

Image layout (offsets authenticated via the manifest's addr fields):
  0x000  manifest            (padded to MANIFEST_REGION)
  MR     secmon TRZM header  (padded to FW_MODULE_HEADER_REGION) | code
  ...    kernel TRZM header  (padded to FW_MODULE_HEADER_REGION) | code

FWM2 layout (little-endian):
  "FWM2" | founder_root(32) | variant_count(u32)
  per variant:
    variant_id(u32)
    image_len(u32) | image[image_len]
    manifest_len(u32)
    proof_count(u32) | proof_node(32) * proof_count
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from trezor_core_tools import firmware_module as fm  # noqa: E402

HW_MODEL = int.from_bytes(b"T3W1", "little")
HEADER_REGION = 0x400  # FW_MODULE_HEADER_REGION
MANIFEST_REGION = 0x400  # reserved region for the manifest at image start
CODE_SIZE = 0x100

VARIANTS = {2: "universal", 3: "bitcoin-only", 4: "prodtest"}


def _module(module_type: int, code: bytes):
    """Return (header_bytes, code) for a synthetic TRZM module. code_hash is a
    single SHA-256 over the whole module code. The variant is authenticated in
    the manifest, not the module header."""
    code_hash = hashlib.sha256(code).digest()
    header = fm._FIXED.pack(
        fm.MAGIC,
        HW_MODEL,
        module_type,
        bytes([1, 0, 0, 0]),
        len(code),
        code_hash,
    )
    return header, code


def _build_variant_image(vid: int):
    """Lay out [manifest | secmon | kernel] and return (image, manifest_bytes)."""
    secmon_hdr, secmon_code = _module(1, b"\xaa" * CODE_SIZE)
    kernel_hdr, kernel_code = _module(2, bytes([vid & 0xFF]) * CODE_SIZE)

    # Module offsets (manifest occupies the first MANIFEST_REGION bytes).
    sec_addr = MANIFEST_REGION
    ker_addr = sec_addr + HEADER_REGION + CODE_SIZE

    entries = [
        # secmon is the secure boot/entry module (FLAG_BOOT).
        {
            "module_type": 1,
            "flags": fm.FW_MANIFEST_ENTRY_FLAG_BOOT,
            "addr": sec_addr,
            "size": CODE_SIZE,
            "header_hash": fm._sha256(secmon_hdr),
        },
        {
            "module_type": 2,
            "flags": 0,
            "addr": ker_addr,
            "size": CODE_SIZE,
            "header_hash": fm._sha256(kernel_hdr),
        },
    ]
    manifest = fm.build_manifest(vid, entries)

    image = bytearray(ker_addr + HEADER_REGION + CODE_SIZE)
    # 0xFF-fill the reserved/padding regions like flash.
    for i in range(len(image)):
        image[i] = 0xFF
    image[0 : len(manifest)] = manifest
    image[sec_addr : sec_addr + len(secmon_hdr)] = secmon_hdr
    image[sec_addr + HEADER_REGION : sec_addr + HEADER_REGION + CODE_SIZE] = secmon_code
    image[ker_addr : ker_addr + len(kernel_hdr)] = kernel_hdr
    image[ker_addr + HEADER_REGION : ker_addr + HEADER_REGION + CODE_SIZE] = kernel_code
    return bytes(image), manifest


def build():
    images, manifests, leaves = {}, {}, {}
    for vid, vname in VARIANTS.items():
        image, manifest = _build_variant_image(vid)
        images[vid] = image
        manifests[vid] = manifest
        leaves[vid] = fm.variant_leaf(manifest)
    root, proofs = fm.build_founder_tree(list(leaves.values()))  # asserts folds
    return images, manifests, leaves, proofs, root


def emit(path: Path) -> None:
    images, manifests, leaves, proofs, root = build()

    print(f"founder firmware_root : {root.hex()}")
    buf = b"FWM2" + root + struct.pack("<I", len(images))
    for vid, vname in VARIANTS.items():
        image, manifest = images[vid], manifests[vid]
        proof = proofs[leaves[vid]]
        print(
            f"  variant {vid:>2} ({vname:<12}) image {len(image)}B "
            f"manifest {len(manifest)}B leaf {leaves[vid].hex()[:12]} "
            f"proof {len(proof)}"
        )
        buf += struct.pack("<I", vid)
        buf += struct.pack("<I", len(image)) + image
        buf += struct.pack("<I", len(manifest))
        buf += struct.pack("<I", len(proof))
        for node in proof:
            buf += node

    path.write_bytes(buf)
    print(f"wrote {path} ({len(buf)} bytes)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("multivariant.vec")
    emit(out)
