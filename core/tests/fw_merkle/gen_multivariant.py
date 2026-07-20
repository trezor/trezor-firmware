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

VARIANTS = {2: "universal", 3: "bitcoin-only", 4: "prodtest"}


def _align(x: int) -> int:
    return (x + CODE_ALIGNMENT - 1) // CODE_ALIGNMENT * CODE_ALIGNMENT


def _build_variant_image(vid: int):
    """Lay out [manifest | secmon code | kernel code] and return
    (image, manifest_bytes). Each manifest entry commits its module directly by
    code_hash = SHA-256 over the module code (no per-module header)."""
    secmon_code = b"\xaa" * CODE_SIZE
    kernel_code = bytes([vid & 0xFF]) * CODE_SIZE

    # Module code offsets (manifest occupies the first MANIFEST_REGION bytes).
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
            "size": CODE_SIZE,
            "code_hash": hashlib.sha256(kernel_code).digest(),
        },
    ]
    manifest = fm.build_manifest(vid, entries)

    image = bytearray(b"\xff" * _align(ker_addr + CODE_SIZE))
    image[0 : len(manifest)] = manifest
    image[sec_addr : sec_addr + CODE_SIZE] = secmon_code
    image[ker_addr : ker_addr + CODE_SIZE] = kernel_code
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
