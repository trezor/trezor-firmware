"""Shared helpers for the Merkle-tree firmware layout (`pq_secure_boot`).

A `firmware.bin` built with the `pq_secure_boot` feature begins with a firmware
manifest ("firmware directory", magic 'TRZD') occupying FW_MANIFEST_REGION,
followed by the module code blobs it describes:

    [ manifest | secmon code | kernel+coreapp code ]

The manifest's directory entry for each module carries the module's code offset
(`addr`), `size`, and `code_hash` (a single SHA-256 over the whole module code).
There is no separate per-module header -- the manifest entry IS the module's
authenticated descriptor, so the commitment is a single hop
(variant leaf -> manifest -> code_hash -> code). The variant leaf is
H(0x00 || manifest); the founder firmware_root is the Merkle tree over the
per-variant leaves.

`fill_manifest()` fills each entry's code_hash from the placed module code (a
build step, see headertool_pq). `firmware_root_multi()` / `build_founder_tree()`
compute the founder root + per-variant proofs (the signer).
"""

from __future__ import annotations

import hashlib
import struct

from trezorlib import merkle_tree

CODE_ALIGNMENT = 0x400
# Reserved region at the very start of the firmware image, holding the manifest
# (matches FW_MANIFEST_REGION in sec/boot_header.h and the *_pq.ld scripts).
FW_MANIFEST_REGION = 0x400

TYPE_NAMES = {1: "secmon", 2: "app (kernel+coreapp)", 3: "prodtest"}
# Variant vocabulary shared with vendor_fw_type_t (sec/image.h) and the model
# vendorheader JSONs. Value 1 (custom) is a FIRST-CLASS variant in the tree
# scheme -- the founder-signed unofficial-app slot (see variant_leaf).
VARIANT_NAMES = {
    0: "none",
    1: "custom",
    2: "universal",
    3: "bitcoin-only",
    4: "prodtest",
    5: "CA",
}

# Firmware variants (fw_variant_t, sec/boot_header.h) == vendor_fw_type_t.
FW_VARIANT_NONE = 0
FW_VARIANT_CUSTOM = 1
FW_VARIANT_UNIVERSAL = 2
FW_VARIANT_BITCOIN_ONLY = 3
FW_VARIANT_PRODTEST = 4

# Module types (fw_module_type_t, sec/boot_header.h). APP is the non-secure
# application (kernel+coreapp); PRODTEST is a standalone secure factory-test image.
FW_MODULE_SECMON = 1
FW_MODULE_APP = 2
FW_MODULE_PRODTEST = 3

# Manifest entry flags (firmware_manifest_entry_t.flags, sec/boot_header.h).
# FLAG_BOOT marks the secure boot/entry module (exactly one per manifest).
FW_MANIFEST_ENTRY_FLAG_BOOT = 0x1


def _sha256(b: bytes | bytearray) -> bytes:
    return hashlib.sha256(b).digest()


def _model_str(hw_model: int) -> str:
    """The hw_model u32 encodes 4 ASCII chars (e.g. 'T3W1')."""
    raw = hw_model.to_bytes(4, "little")
    text = raw.decode("ascii", "replace").rstrip("\x00")
    return text if text.isprintable() else f"0x{hw_model:08x}"


# --- Variant manifest ("firmware directory") ---------------------------------
#
# The variant leaf is a manifest: a directory of the variant's modules plus
# variant-level authenticated fields (firmware_variant,
# translations_root). Each directory entry references its module directly by
# code_hash = SHA-256 over the whole module code (there is no per-module TRZM
# header). The variant leaf is H(0x00 || manifest); the founder tree combines
# variant leaves.
#
# Layout (little-endian), must byte-match the on-device manifest:
#   magic 'TRZD' | firmware_variant u32 | firmware_version[4]
#   | translations_root[32] | module_count u32 | entry[module_count]
#   entry: module_type u32 | flags u32 | addr u32 | size u32 | code_hash[32]
# firmware_version is major,minor,patch,build (mirrors the kernel+coreapp build);
# it is authenticated in the variant leaf and lets the install confirm show the
# firmware version in phase 1 (before the module code is streamed).

MANIFEST_MAGIC = b"TRZD"
_MANIFEST_FIXED = struct.Struct("<4sI4s32sI")
_MANIFEST_ENTRY = struct.Struct("<IIII32s")
_ZERO32 = b"\x00" * 32
_ZERO4 = b"\x00" * 4


def build_manifest(
    firmware_variant: int,
    entries: list[dict],
    translations_root: bytes = _ZERO32,
    firmware_version: bytes = _ZERO4,
) -> bytes:
    """Serialize a variant manifest. `entries` is a list of dicts with keys
    module_type, flags, addr, size, code_hash (32 bytes), in role order.
    `firmware_version` is the 4-byte major,minor,patch,build."""
    buf = _MANIFEST_FIXED.pack(
        MANIFEST_MAGIC,
        firmware_variant,
        firmware_version,
        translations_root,
        len(entries),
    )
    for e in entries:
        buf += _MANIFEST_ENTRY.pack(
            e["module_type"],
            e.get("flags", 0),
            e["addr"],
            e["size"],
            e["code_hash"],
        )
    return buf


def read_manifest(fw: bytes | bytearray) -> bytes:
    """Read the manifest bytes stored at the start of a firmware image (the
    authenticated bytes the device hashes for the variant leaf)."""
    magic, _v, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("no manifest at the firmware image start")
    return bytes(fw[0 : _MANIFEST_FIXED.size + mc * _MANIFEST_ENTRY.size])


def manifest_entries(fw: bytes | bytearray) -> list[dict]:
    """Parse the manifest directory into a list of entry dicts (module_type,
    flags, addr, size, code_hash), in manifest order. Replaces the old TRZM
    module-chain scan -- the manifest IS the directory now."""
    magic, _v, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("no manifest at the firmware image start")
    entries = []
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype, flags, addr, size, code_hash = _MANIFEST_ENTRY.unpack_from(fw, eoff)
        entries.append(
            {
                "module_type": mtype,
                "flags": flags,
                "addr": addr,
                "size": size,
                "code_hash": code_hash,
            }
        )
    return entries


def format_manifest(manifest: bytes) -> str:
    """Human-readable dump of the firmware manifest ("firmware directory", TRZD):
    the authenticated variant + subtree roots and the per-module directory (each
    entry's role/flags/addr/size and committed code_hash). A ZEROED
    kernel+coreapp code_hash marks a custom/wildcard (unofficial) manifest."""
    magic, variant, ver, tr_root, mc = _MANIFEST_FIXED.unpack_from(
        manifest, 0
    )
    if magic != MANIFEST_MAGIC:
        return "(no manifest -- not a TRZD image)"

    def _root(b: bytes) -> str:
        return "zero (reserved)" if not any(b) else bytes(b).hex()

    vname = VARIANT_NAMES.get(variant, f"variant{variant}")
    ver_str = ".".join(str(b) for b in ver)
    lines = [
        "firmware manifest (TRZD)",
        f"  firmware_variant : {variant} ({vname})",
        f"  firmware_version : {ver_str}",
        f"  translations_root: {_root(tr_root)}",
        f"  module_count     : {mc}",
    ]
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype, flags, addr, size, ch = _MANIFEST_ENTRY.unpack_from(manifest, eoff)
        tname = TYPE_NAMES.get(mtype, f"type{mtype}")
        ch_s = "ZEROED (custom/wildcard)" if not any(ch) else bytes(ch).hex()
        boot = " BOOT" if flags & FW_MANIFEST_ENTRY_FLAG_BOOT else ""
        lines.append(
            f"  [{i}] {tname:14} flags 0x{flags:x}{boot} addr 0x{addr:06x} "
            f"size {size:>8}  code_hash {ch_s}"
        )
    return "\n".join(lines)


def manifest_variant(manifest: bytes) -> int:
    """The authenticated firmware_variant (fw_variant_t) stored in a manifest."""
    magic, variant, _ver, _tr, _mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("not a manifest (bad magic)")
    return variant


def manifest_version(manifest: bytes) -> tuple[int, int, int, int]:
    """The authenticated firmware version (major, minor, patch, build)."""
    magic, _v, ver, _tr, _mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("not a manifest (bad magic)")
    return tuple(ver)


def is_custom_firmware(fw: bytes | bytearray) -> bool:
    """True iff the firmware's authenticated variant is the CUSTOM slot
    (FW_VARIANT_CUSTOM). Custom is a first-class variant now -- not a per-module
    wildcard -- so this is a simple variant check."""
    try:
        return manifest_variant(read_manifest(fw)) == FW_VARIANT_CUSTOM
    except ValueError:
        return False


def fill_manifest(fw: bytearray) -> bytearray:
    """Patch the compile-time manifest template (from manifest_header.S) in place.

    The template already carries the static fields (magic, firmware_variant,
    module_count, firmware_version) and each entry's module_type + flags + addr +
    size (the latter two from linker symbols). This fills each entry's code_hash
    (single SHA-256 over the module code at addr..addr+size) -- ALWAYS the real
    code hash, including the kernel+coreapp of a CUSTOM variant (its real hash is
    the creator's integrity hash). The custom slot's founder-signed leaf zeroes
    the app hash only for the AUTHENTICITY fold (see variant_leaf), never in the
    on-flash bytes. translations_root is left as set by the template
    (0 until that subtree exists)."""
    magic, _variant, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError(
            "no manifest template at the image start (manifest_header.S missing?)"
        )
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        _mtype, _flags, addr, size, _ch = _MANIFEST_ENTRY.unpack_from(fw, eoff)
        # Entry layout: module_type(4) flags(4) addr(4) size(4) code_hash(32).
        code = bytes(fw[addr : addr + size])
        fw[eoff + 16 : eoff + 48] = _sha256(code)
    return fw


def authenticity_manifest(manifest: bytes) -> bytes:
    """The manifest bytes the variant leaf is computed over: identical to
    `manifest`, EXCEPT for the CUSTOM variant, where EVERYTHING the creator
    controls is zeroed so any creator app folds to the one founder-signed slot:
    the manifest firmware_version (offset 8, 4 bytes) and the kernel+coreapp
    (FW_MODULE_APP) entry's size + code_hash (the entry's contiguous tail,
    offset +12..+48). The app's module_type/flags/addr and the whole secmon entry
    stay real. Mirrors boot_header_variant_leaf() in boot_header_merkle.h
    byte-for-byte."""
    if manifest_variant(manifest) != FW_VARIANT_CUSTOM:
        return manifest
    _magic, _v, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    buf = bytearray(manifest)
    # firmware_version (creator's app version) -> zero.
    buf[8:12] = b"\x00" * 4
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype = struct.unpack_from("<I", manifest, eoff)[0]
        if mtype == FW_MODULE_APP:
            # app entry size (+12, 4B) + code_hash (+16, 32B) -> zero.
            buf[eoff + 12 : eoff + 48] = b"\x00" * 36
            break
    return bytes(buf)


def variant_leaf(manifest: bytes) -> bytes:
    """The variant's Merkle leaf: H(0x00 || authenticity_manifest). This is the
    node the founder tree combines and the device folds up to firmware_root. For
    the custom variant the app code_hash is zeroed first (see
    authenticity_manifest)."""
    return merkle_tree.leaf_hash(authenticity_manifest(manifest))


# --- Founder (multi-variant) firmware_root -----------------------------------
#
# firmware_root is a two-level Merkle tree:
#   * per variant: variant leaf = H(0x00 || manifest)   (see variant_leaf)
#   * founder:     firmware_root = tree over the variant leaves
# The founder level combines the variant leaves AS NODE HASHES (sorted-pair
# internal_hash), NOT re-leaf-hashed -- because the device folds its variant leaf
# directly (firmware_manifest_authentic, no leaf_hash). trezorlib's MerkleTree
# always leaf-hashes its inputs, so we build the founder level with a pre-hashed
# leaf and reuse trezorlib's Node + the same sort/pair construction.


class _PreHashedLeaf:
    """A founder-tree leaf whose tree_hash IS a precomputed variant leaf (not
    leaf_hash(value)). Duck-types trezorlib.merkle_tree.NodeType."""

    def __init__(self, node_hash: bytes) -> None:
        self.tree_hash = node_hash
        self.proof: list[bytes] = []

    def add_to_proof_list(self, proof_entry: bytes) -> None:
        self.proof.append(proof_entry)


def _fold_proof(node: bytes, proof: list[bytes]) -> bytes:
    """Fold a variant leaf up to firmware_root, exactly as the device does
    (firmware_manifest_authentic): sequential sorted-pair internal_hash."""
    for sibling in proof:
        node = merkle_tree.internal_hash(node, sibling)
    return node


def build_founder_tree(
    variant_leaves: list[bytes],
) -> tuple[bytes, dict[bytes, list[bytes]]]:
    """Build the founder firmware_root over per-variant leaves.

    Returns (firmware_root, {variant_leaf: proof}). Each proof is the co-path of
    that variant leaf, in the order the device folds it. variant_leaves must be
    distinct (variants differ in their kernel+coreapp code_hash, so their
    manifests -- and thus leaves -- do)."""
    if not variant_leaves:
        raise ValueError("need at least one variant leaf")
    if len(set(variant_leaves)) != len(variant_leaves):
        raise ValueError("duplicate variant leaves")

    leaves = [_PreHashedLeaf(r) for r in variant_leaves]
    leaves.sort(key=lambda leaf: leaf.tree_hash)
    entries = {leaf.tree_hash: leaf for leaf in leaves}

    level = leaves
    while len(level) > 1:
        nxt = []
        while len(level) >= 2:
            left, right, *level = level
            nxt.append(merkle_tree.Node(left, right))
        nxt.extend(level)  # carry an odd node up
        level = nxt

    root = level[0].tree_hash
    proofs = {r: entries[r].proof for r in variant_leaves}
    # Self-consistency: every variant leaf must fold to the founder root.
    for r, proof in proofs.items():
        assert _fold_proof(r, proof) == root, "founder-tree proof mismatch"
    return root, proofs


def firmware_root_multi(
    variant_images: dict[str, bytes],
) -> tuple[bytes, dict[str, tuple[bytes, list[bytes]]]]:
    """Given {variant_name: firmware.bin (manifest-filled)}, return
    (firmware_root, {variant_name: (variant_leaf, proof)}). The variant leaf is
    the manifest leaf H(0x00 || manifest)."""
    leaves = {
        name: variant_leaf(read_manifest(fw)) for name, fw in variant_images.items()
    }
    root, proofs = build_founder_tree(list(leaves.values()))
    return root, {name: (lf, proofs[lf]) for name, lf in leaves.items()}
