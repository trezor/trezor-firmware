#!/usr/bin/env python3
"""Generate the FWM3 multi-variant firmware_root cross-validation vector.

Synthetic images [manifest | secmon code | kernel code] per variant; the leaf is
H(0x00 || manifest) and code_hash is the smart-hashing chain over the module
code. Replayed by crossvalidate.c through the real firmware_verify_manifest.

FWM3 layout (little-endian):
  "FWM3" | founder_root(32) | variant_count(u32)
  per variant: variant_id(u32) | image_len(u32) | image | manifest_len(u32) |
               alt_len(u32) | alt_image (custom only, else 0) |
               proof_count(u32) | proof_node(32) * proof_count
  then once: noapp_len(u32) | noapp_manifest | noapp_leaf(32)
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from trezor_core_tools import firmware_module as fm  # noqa: E402

MANIFEST_REGION = 0x400  # reserved region for the manifest at image start
CODE_ALIGNMENT = 0x400
CODE_SIZE = 0x100
# 100 gives a partial last chunk; deliberately not a device-valid chunk size.
CHUNK_SIZE_TEST = 100

# Includes CUSTOM (1): its app code_hash is zeroed inside the founder leaf.
VARIANTS = {1: "custom", 2: "universal", 3: "bitcoin-only", 4: "prodtest"}


def _align(x: int) -> int:
    return (x + CODE_ALIGNMENT - 1) // CODE_ALIGNMENT * CODE_ALIGNMENT


def _build_variant_image(
    vid: int,
    version: bytes = b"\x01\x00\x00\x00",
    app_size: int = CODE_SIZE,
    app_byte: int | None = None,
):
    """Lay out [manifest | secmon code | kernel code]; return (image, manifest)."""
    secmon_code = b"\xaa" * CODE_SIZE
    kernel_code = bytes([vid & 0xFF if app_byte is None else app_byte]) * app_size

    # The app addr depends only on the fixed secmon size, so it is stable
    # across app sizes.
    sec_addr = MANIFEST_REGION
    ker_addr = _align(sec_addr + CODE_SIZE)

    entries = [
        # secmon is the boot module (FLAG_BOOT).
        {
            "module_type": 1,
            "flags": fm.FW_MANIFEST_ENTRY_FLAG_BOOT,
            "addr": sec_addr,
            "chunk_size": CHUNK_SIZE_TEST,
            "size": CODE_SIZE,
            "code_hash": fm.module_code_hash(secmon_code, CHUNK_SIZE_TEST),
        },
        {
            "module_type": 2,
            "flags": 0,
            "addr": ker_addr,
            "chunk_size": CHUNK_SIZE_TEST,
            "size": app_size,
            "code_hash": fm.module_code_hash(kernel_code, CHUNK_SIZE_TEST),
        },
    ]
    # VARIANTS is keyed by the small id; the manifest carries the hardened codeword.
    manifest = fm.build_manifest(
        fm.FW_VARIANT_SEC[vid], entries, firmware_version=version
    )

    image = bytearray(b"\xff" * _align(ker_addr + app_size))
    image[0 : len(manifest)] = manifest
    image[sec_addr : sec_addr + CODE_SIZE] = secmon_code
    image[ker_addr : ker_addr + app_size] = kernel_code
    return bytes(image), manifest


def _build_noapp_manifest() -> bytes:
    """A CUSTOM manifest with only a SECMON entry: valid, but nothing to zero."""
    secmon_code = b"\xaa" * CODE_SIZE
    entries = [
        {
            "module_type": 1,
            "flags": fm.FW_MANIFEST_ENTRY_FLAG_BOOT,
            "addr": MANIFEST_REGION,
            "chunk_size": CHUNK_SIZE_TEST,
            "size": CODE_SIZE,
            "code_hash": fm.module_code_hash(secmon_code, CHUNK_SIZE_TEST),
        },
    ]
    return fm.build_manifest(
        fm.FW_VARIANT_SEC[1], entries, firmware_version=b"\x07\x07\x07\x07"
    )


def build():
    images, manifests, leaves, alts = {}, {}, {}, {}
    for vid in VARIANTS:
        if vid == fm.FW_VARIANT_CUSTOM:
            # The custom leaf zeroes app version/size/code_hash, so an alt app
            # differing in all three must give the same leaf.
            image, manifest = _build_variant_image(
                vid, version=b"\x02\x01\x00\x00", app_size=CODE_SIZE
            )
            alt_image, alt_manifest = _build_variant_image(
                vid, version=b"\x09\x09\x09\x09", app_size=CODE_SIZE * 2, app_byte=0x5A
            )
            assert fm.variant_leaf(manifest) == fm.variant_leaf(alt_manifest), (
                "custom leaf is not app-agnostic (version/size/code_hash not zeroed?)"
            )
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
    buf = b"FWM3" + root + struct.pack("<I", len(images))
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

    noapp = _build_noapp_manifest()
    # Not asserted here: whether it is hashed verbatim is what the C side is
    # asked to agree about.
    noapp_leaf = fm.variant_leaf(noapp)
    print(f"  no-APP custom manifest {len(noapp)}B leaf {noapp_leaf.hex()[:12]}")
    buf += struct.pack("<I", len(noapp)) + noapp + noapp_leaf

    path.write_bytes(buf)
    print(f"wrote {path} ({len(buf)} bytes)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("multivariant.vec")
    emit(out)
