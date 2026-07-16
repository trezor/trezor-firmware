"""Shared helpers for the Merkle-tree firmware layout (`pq_secure_boot`).

A `firmware.bin` built with the `pq_secure_boot` feature is a chain of
self-describing modules, each `[TRZM header | code]`:

    [ secmon module ] [ kernel+coreapp module ]

The static header fields (magic, model, type, version, code_size) are emitted at
build time by `module_header.S`. What is filled in afterwards is each header's
`code_hash` (a single SHA-256 over the whole module code). Once filled, the module
leaf is `H(0x00 || header)` and the firmware Merkle root is the tree over those
leaves.

`fill_modules()` performs the fill (a build step, see headertool_pq).
`firmware_root()` recomputes the root from an already-filled image (the signer).
"""

from __future__ import annotations

import hashlib
import struct

from trezorlib import merkle_tree

MAGIC = b"TRZM"
HEADER_REGION = 0x400  # reserved header region in the image (module_header.S)
CODE_ALIGNMENT = 0x400
# Reserved region at the very start of the firmware image, holding the manifest
# (matches FW_MANIFEST_REGION in sec/boot_header.h and the *_pq.ld scripts).
FW_MANIFEST_REGION = 0x400

TYPE_NAMES = {1: "secmon", 2: "app (kernel+coreapp)", 3: "prodtest"}
# Variant vocabulary shared with vendor_fw_type_t (sec/image.h) and the model
# vendorheader JSONs. Value 1 (custom/unsafe) is the FW_TYPE_CUSTOM_FLAG axis in
# the tree scheme, not a variant, but is named here for completeness.
VARIANT_NAMES = {
    0: "none",
    1: "custom",
    2: "universal",
    3: "bitcoin-only",
    4: "prodtest",
    5: "CA",
}

# TRZM header (little-endian): magic, hw_model, module_type, version[4],
# code_size, code_hash[32]  = 52 bytes. code_hash is a single SHA-256 over the
# whole module code (no per-chunk hashes). (The firmware variant is NOT in the
# module header -- it is authenticated in the manifest.)
_FIXED = struct.Struct("<4sII4sI32s")
OFF_CODE_HASH = 20


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def parse_header(fw: bytes | bytearray, off: int) -> dict:
    magic, hw, mtype, ver, code_size, code_hash = _FIXED.unpack_from(fw, off)
    if magic != MAGIC:
        raise ValueError(f"no TRZM header at 0x{off:x}")
    return {
        "off": off,
        "hw_model": hw,
        "module_type": mtype,
        "version": tuple(ver),
        "code_size": code_size,
        "code_hash": code_hash,
    }


def _model_str(hw_model: int) -> str:
    """The hw_model u32 encodes 4 ASCII chars (e.g. 'T3W1')."""
    raw = hw_model.to_bytes(4, "little")
    text = raw.decode("ascii", "replace").rstrip("\x00")
    return text if text.isprintable() else f"0x{hw_model:08x}"


def format_module(fw: bytes | bytearray, h: dict) -> str:
    """A human-readable dump of a single TRZM module header."""
    type_name = TYPE_NAMES.get(h["module_type"], f"type{h['module_type']}")
    version = ".".join(str(v) for v in h["version"])
    lines = [
        f"TRZM module @ 0x{h['off']:06x}  ({type_name})",
        f"  hw_model     : {_model_str(h['hw_model'])}",
        f"  module_type  : {h['module_type']} ({type_name})",
        f"  version      : {version}",
        f"  code_size    : {h['code_size']} bytes",
        f"  code_hash    : {h['code_hash'].hex()}",
    ]
    if any(h["code_hash"]):
        leaf = merkle_tree.leaf_hash(header_bytes(fw, h))
        lines.append(f"  leaf         : {leaf.hex()}")
    return "\n".join(lines)


def find_modules(fw: bytes | bytearray) -> list[dict]:
    """Walk the module chain, skipping any leading manifest region.

    The firmware image begins with the manifest (magic 'TRZD') occupying
    FW_MANIFEST_REGION; the first module (secmon, 'TRZM') follows. Scan forward in
    CODE_ALIGNMENT steps to the first TRZM header, then walk the chain. (Also
    handles a bare module chain with no manifest, where the first TRZM is at 0.)
    """
    mods = []
    off = 0
    while off + 4 <= len(fw) and fw[off : off + 4] != MAGIC:
        off += CODE_ALIGNMENT
    while off + _FIXED.size <= len(fw) and fw[off : off + 4] == MAGIC:
        h = parse_header(fw, off)
        mods.append(h)
        nxt = off + HEADER_REGION + h["code_size"]
        nxt = (nxt + CODE_ALIGNMENT - 1) // CODE_ALIGNMENT * CODE_ALIGNMENT
        # skip padding until the next module header (or end of image)
        while nxt + 4 <= len(fw) and fw[nxt : nxt + 4] != MAGIC:
            nxt += CODE_ALIGNMENT
        off = nxt
    return mods


def fill_module(fw: bytearray, h: dict) -> bytes:
    """Fill code_hash (single SHA-256 over the whole module code) in place; return
    the authenticated header bytes (the value the module leaf is computed over)."""
    off, code_size = h["off"], h["code_size"]
    code_off = off + HEADER_REGION
    code_hash = _sha256(bytes(fw[code_off : code_off + code_size]))
    fw[off + OFF_CODE_HASH : off + OFF_CODE_HASH + 32] = code_hash
    h["code_hash"] = code_hash
    return header_bytes(fw, h)


def header_bytes(fw: bytes | bytearray, h: dict) -> bytes:
    """The authenticated header bytes (the fixed TRZM header) of a module."""
    return bytes(fw[h["off"] : h["off"] + _FIXED.size])


def fill_modules(fw: bytearray) -> list[dict]:
    """Fill every module header in the image in place. Returns the module list
    (with code_hash populated)."""
    mods = find_modules(fw)
    for h in mods:
        fill_module(fw, h)
    return mods


def module_leaves(fw: bytes | bytearray, mods: list[dict] | None = None) -> list[bytes]:
    """The per-module leaf values (authenticated header bytes) of a filled image."""
    if mods is None:
        mods = find_modules(fw)
    return [header_bytes(fw, h) for h in mods]


def module_headers_blob(fw: bytes | bytearray, mods: list[dict] | None = None) -> bytes:
    """The firmware manifest ("firmware directory") stored at the image start --
    the opaque preamble blob sent in a FirmwareBegin. The device authenticates
    it (variant leaf -> firmware_root) and reads the variant/directory from it."""
    return read_manifest(fw)


def variant_root(fw: bytes | bytearray, mods: list[dict] | None = None) -> bytes:
    """Merkle root combining all module leaves present in this image (secmon +
    kernel+coreapp) -- i.e. the root of one firmware variant.

    The founder-committed `firmware_root` (folded into the bootloader header)
    spans all variants (universal, bitcoin-only, prodtest, ...); each variant
    contributes this variant_root as a subtree. See `build_founder_tree`.
    """
    return merkle_tree.MerkleTree(module_leaves(fw, mods)).get_root_hash()


# --- Variant manifest ("firmware directory") ---------------------------------
#
# The variant leaf is a manifest: a directory of the variant's modules plus
# variant-level authenticated fields (firmware_variant, app_root,
# translations_root). It keeps the TRZM module headers -- each directory entry
# references its module by header_hash = SHA256(TRZM header), which commits the
# module's code_hash (SHA-256 over the whole module code). The variant leaf is
# H(0x00 || manifest); the founder tree combines variant leaves.
#
# Layout (little-endian), must byte-match the on-device manifest:
#   magic 'TRZD' | firmware_variant u32 | firmware_version[4] | app_root[32]
#   | translations_root[32] | module_count u32 | entry[module_count]
#   entry: module_type u32 | flags u32 | addr u32 | size u32 | header_hash[32]
# firmware_version is major,minor,patch,build (mirrors the kernel+coreapp module
# header); it is authenticated in the variant leaf and lets the install confirm
# show the firmware version in phase 1 (before the module code is streamed).

MANIFEST_MAGIC = b"TRZD"
_MANIFEST_FIXED = struct.Struct("<4sI4s32s32sI")
_MANIFEST_ENTRY = struct.Struct("<IIII32s")
_ZERO32 = b"\x00" * 32
_ZERO4 = b"\x00" * 4


def build_manifest(
    firmware_variant: int,
    entries: list[dict],
    app_root: bytes = _ZERO32,
    translations_root: bytes = _ZERO32,
    firmware_version: bytes = _ZERO4,
) -> bytes:
    """Serialize a variant manifest. `entries` is a list of dicts with keys
    module_type, flags, addr, size, header_hash (32 bytes), in role order.
    `firmware_version` is the 4-byte major,minor,patch,build."""
    buf = _MANIFEST_FIXED.pack(
        MANIFEST_MAGIC,
        firmware_variant,
        firmware_version,
        app_root,
        translations_root,
        len(entries),
    )
    for e in entries:
        buf += _MANIFEST_ENTRY.pack(
            e["module_type"],
            e.get("flags", 0),
            e["addr"],
            e["size"],
            e["header_hash"],
        )
    return buf


def read_manifest(fw: bytes | bytearray) -> bytes:
    """Read the manifest bytes stored at the start of a firmware image (the
    authenticated bytes the device hashes for the variant leaf)."""
    magic, _v, _ver, _ar, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("no manifest at the firmware image start")
    return bytes(fw[0 : _MANIFEST_FIXED.size + mc * _MANIFEST_ENTRY.size])


def format_manifest(manifest: bytes) -> str:
    """Human-readable dump of the firmware manifest ("firmware directory", TRZD):
    the authenticated variant + subtree roots and the per-module directory (each
    entry's role/flags/addr/size and committed header_hash). A ZEROED
    kernel+coreapp header_hash marks a custom/wildcard (unofficial) manifest."""
    magic, variant, ver, app_root, tr_root, mc = _MANIFEST_FIXED.unpack_from(
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
        f"  app_root         : {_root(app_root)}",
        f"  translations_root: {_root(tr_root)}",
        f"  module_count     : {mc}",
    ]
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype, flags, addr, size, hh = _MANIFEST_ENTRY.unpack_from(manifest, eoff)
        tname = TYPE_NAMES.get(mtype, f"type{mtype}")
        hh_s = "ZEROED (custom/wildcard)" if not any(hh) else bytes(hh).hex()
        boot = " BOOT" if flags & FW_MANIFEST_ENTRY_FLAG_BOOT else ""
        lines.append(
            f"  [{i}] {tname:14} flags 0x{flags:x}{boot} addr 0x{addr:06x} "
            f"size {size:>8}  header_hash {hh_s}"
        )
    return "\n".join(lines)


def manifest_variant(manifest: bytes) -> int:
    """The authenticated firmware_variant (fw_variant_t) stored in a manifest."""
    magic, variant, _ver, _ar, _tr, _mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("not a manifest (bad magic)")
    return variant


def manifest_version(manifest: bytes) -> tuple[int, int, int, int]:
    """The authenticated firmware version (major, minor, patch, build)."""
    magic, _v, ver, _ar, _tr, _mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("not a manifest (bad magic)")
    return tuple(ver)


def manifest_kernel_is_wildcard(manifest: bytes) -> bool:
    """True if the manifest's kernel+coreapp entry is a FILLED wildcard (addr set,
    header_hash zeroed) -- i.e. a custom manifest. Distinct from an unfilled
    template (addr also zero), so it does not misfire on a fresh build."""
    magic, _v, _ver, _ar, _tr, mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    if magic != MANIFEST_MAGIC:
        return False
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype, _flags, addr, _size, hh = _MANIFEST_ENTRY.unpack_from(manifest, eoff)
        if mtype == FW_MODULE_APP:
            return addr != 0 and not any(hh)
    return False


# Module types (fw_module_type_t, sec/boot_header.h). APP is the non-secure
# application (kernel+coreapp); PRODTEST is a standalone secure factory-test image.
FW_MODULE_SECMON = 1
FW_MODULE_APP = 2
FW_MODULE_PRODTEST = 3

# Manifest entry flags (firmware_manifest_entry_t.flags, sec/boot_header.h).
# FLAG_BOOT marks the secure boot/entry module (exactly one per manifest).
FW_MANIFEST_ENTRY_FLAG_BOOT = 0x1


def is_custom_firmware(fw: bytes | bytearray) -> bool:
    """True iff a NON-secmon module (kernel+coreapp) deviates from its own
    manifest's committed header_hash -- i.e. this image must be installed as
    CUSTOM/unofficial. Replays the device's per-module bind: header_hash ==
    SHA256(the 52-byte TRZM header at the entry's addr).

    The manifest itself is still the (official) one that folds to the founder
    firmware_root; only a module's code differs. A secmon deviation is NOT
    "custom" -- the device rejects it outright (the secure monitor must stay
    official) -- so it is ignored here (the install will simply fail)."""
    manifest = read_manifest(fw)
    _magic, _variant, _ver, _ar, _tr, mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype, _flags, addr, _size, header_hash = _MANIFEST_ENTRY.unpack_from(
            manifest, eoff
        )
        if mtype == FW_MODULE_SECMON:
            continue
        if _sha256(header_bytes(fw, {"off": addr})) != header_hash:
            return True
    return False


def fill_manifest(
    fw: bytearray, mods: list[dict] | None = None, custom: bool = False
) -> bytearray:
    """Patch the compile-time manifest template (from manifest_header.S) in place.

    The template already carries the static fields (magic, firmware_variant,
    module_count, and each entry's module_type + flags). This fills the per-entry
    addr/size/header_hash from the (code_hash-filled) modules, and verifies the static
    directory matches the actual module chain. app_root/translations_root are left
    as set by the template (0 until those subtrees exist).

    With `custom`, the kernel+coreapp entry's header_hash is ZEROED (a wildcard):
    the manifest is still (dev-)signed and folds to firmware_root, but NO
    kernel+coreapp matches a zero hash, so any firmware installed against it is
    treated as custom/unofficial. The secmon entry stays a real hash (it must
    always conform)."""
    if mods is None:
        mods = find_modules(fw)
    magic, _variant, _ver, _ar, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError(
            "no manifest template at the image start (manifest_header.S missing?)"
        )
    if mc != len(mods):
        raise ValueError(f"manifest module_count {mc} != {len(mods)} modules")
    # firmware_version is emitted at build time in manifest_header.S (from
    # version.h -- the SAME source as the kernel+coreapp module header). It is not
    # post-filled here; instead verify the two agree, so a desync between the
    # manifest and module .S is caught at build time. (offset 8 = after magic +
    # variant.)
    kc = next((h for h in mods if h["module_type"] == FW_MODULE_APP), None)
    if kc is not None:
        manifest_ver = tuple(fw[8:12])
        if manifest_ver != tuple(kc["version"]):
            raise ValueError(
                f"manifest firmware_version {manifest_ver} != kernel+coreapp "
                f"module version {tuple(kc['version'])}"
            )
    for i, h in enumerate(mods):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype = struct.unpack_from("<I", fw, eoff)[0]
        if mtype != h["module_type"]:
            raise ValueError(
                f"manifest entry {i} module_type {mtype} != module {h['module_type']}"
            )
        # Entry layout: module_type(4) flags(4) addr(4) size(4) header_hash(32).
        struct.pack_into("<II", fw, eoff + 8, h["off"], h["code_size"])
        if custom and h["module_type"] == FW_MODULE_APP:
            fw[eoff + 16 : eoff + 48] = b"\x00" * 32  # wildcard -> always custom
        else:
            fw[eoff + 16 : eoff + 48] = _sha256(header_bytes(fw, h))
    return fw


def variant_leaf(manifest: bytes) -> bytes:
    """The variant's Merkle leaf: H(0x00 || manifest). This is the node the
    founder tree combines and the device folds up to firmware_root."""
    return merkle_tree.leaf_hash(manifest)


# --- Founder (multi-variant) firmware_root -----------------------------------
#
# firmware_root is a two-level Merkle tree:
#   * per variant: variant leaf = H(0x00 || manifest)   (see variant_leaf)
#   * founder:     firmware_root = tree over the variant leaves
# The founder level combines the variant_roots AS NODE HASHES (sorted-pair
# internal_hash), NOT re-leaf-hashed -- because the device folds its variant_root
# directly in boot_header_calc_firmware_root's phase 2 (no leaf_hash). trezorlib's
# MerkleTree always leaf-hashes its inputs, so we build the founder level with a
# pre-hashed leaf and reuse trezorlib's Node + the same sort/pair construction.


class _PreHashedLeaf:
    """A founder-tree leaf whose tree_hash IS a precomputed variant_root (not
    leaf_hash(value)). Duck-types trezorlib.merkle_tree.NodeType."""

    def __init__(self, node_hash: bytes) -> None:
        self.tree_hash = node_hash
        self.proof: list[bytes] = []

    def add_to_proof_list(self, proof_entry: bytes) -> None:
        self.proof.append(proof_entry)


def _fold_proof(node: bytes, proof: list[bytes]) -> bytes:
    """Fold a variant_root up to firmware_root, exactly as the device does
    (boot_header_calc_firmware_root phase 2): sequential sorted-pair internal_hash.
    """
    for sibling in proof:
        node = merkle_tree.internal_hash(node, sibling)
    return node


def build_founder_tree(
    variant_roots: list[bytes],
) -> tuple[bytes, dict[bytes, list[bytes]]]:
    """Build the founder firmware_root over per-variant roots.

    Returns (firmware_root, {variant_root: proof}). Each proof is the co-path of
    that variant_root, in the order the device folds it. variant_roots must be
    distinct (variants differ in their kernel+coreapp leaf, so their roots do).
    """
    if not variant_roots:
        raise ValueError("need at least one variant_root")
    if len(set(variant_roots)) != len(variant_roots):
        raise ValueError("duplicate variant_roots")

    leaves = [_PreHashedLeaf(r) for r in variant_roots]
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
    proofs = {r: entries[r].proof for r in variant_roots}
    # Self-consistency: every variant_root must fold to the founder root.
    for r, proof in proofs.items():
        assert _fold_proof(r, proof) == root, "founder-tree proof mismatch"
    return root, proofs


def firmware_root_multi(
    variant_images: dict[str, bytes],
) -> tuple[bytes, dict[str, tuple[bytes, list[bytes]]]]:
    """Given {variant_name: firmware.bin (header-filled)}, return
    (firmware_root, {variant_name: (variant_leaf, proof)}). The variant leaf is
    the manifest leaf H(0x00 || manifest)."""
    leaves = {
        name: variant_leaf(read_manifest(fw)) for name, fw in variant_images.items()
    }
    root, proofs = build_founder_tree(list(leaves.values()))
    return root, {name: (lf, proofs[lf]) for name, lf in leaves.items()}
