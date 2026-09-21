"""Shared helpers for the Merkle-tree firmware layout (`pq_secure_boot`).

Image layout: [ manifest | firmware proof | secmon code | kernel+coreapp code ].
Variant leaf = H(0x00 || manifest); see docs/core/embed-arch/firmware-merkle-tree.md.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from trezorlib import merkle_tree
from trezorlib.firmware import pq_secure

CODE_ALIGNMENT = 0x400
# Manifest + proof region at the image start; must match FW_MANIFEST_REGION in
# sec/boot_header.h and the *_pq.ld scripts.
FW_MANIFEST_REGION = 0x400
# == FW_MANIFEST_PROOF_MAX_NODES in sec/boot_header.h (up to 16 variants).
FW_MANIFEST_PROOF_MAX_NODES = 4

TYPE_NAMES = {1: "secmon", 2: "app (kernel+coreapp)", 3: "prodtest"}
# Keyed by the hardened codeword the manifest carries (fw_variant_sec_t).
VARIANT_NAMES = {
    0x00000000: "invalid",
    0xCCCCCCCC: "none",
    0x33333333: "custom",
    0x5A5A5A5A: "universal",
    0xA5A5A5A5: "bitcoin-only",
    0x66666666: "prodtest",
}

# --- Release container ('bundle.json') ---------------------------------------
#
# Unsigned by design: the boot-header signature is the trust root, so a tampered
# container is a fail-closed DoS, never a forgery. Fields are routing, not
# authority. See docs/core/build/xtask.md.
CONTAINER_MAGIC = "TRZL"
# Bump on any incompatible change; readers reject unknown versions.
CONTAINER_VERSION = 1
# The cross-model set written by `xtask release --promote`.
CONTAINER_SET_MAGIC = f"{CONTAINER_MAGIC}-set"
# Name the release writer gives the bootloader; readers use `bootloader.file`.
CONTAINER_DEFAULT_BOOTLOADER = "bootloader.bin"


def check_container(doc: dict, path: Path | str, *, is_set: bool = False) -> dict:
    """Reject a container of unknown format/version (checked first), return it."""
    want = CONTAINER_SET_MAGIC if is_set else CONTAINER_MAGIC
    got = doc.get("format")
    if got is None:
        raise SystemExit(
            f"{path} has no `format` -- it predates the versioned release "
            f"container, rebuild or re-promote it"
        )
    if got != want:
        raise SystemExit(f"{path}: format is {got!r}, expected {want!r}")
    version = doc.get("format_version")
    if version != CONTAINER_VERSION:
        raise SystemExit(
            f"{path} is container v{version}, but this tool speaks "
            f"v{CONTAINER_VERSION} -- rebuild or re-promote it"
        )
    return doc


def container_models(doc: dict, path: Path | str) -> dict[str, dict]:
    """Read a container as ``{model: body}``, accepting either shape."""
    if "models" in doc:
        check_container(doc, path, is_set=True)
        out = {}
        for model, body in doc["models"].items():
            check_container(body, f"{path} [{model}]")
            if body.get("model") != model:
                raise SystemExit(
                    f"{path}: the entry filed under {model} names model "
                    f"{body.get('model')!r}"
                )
            out[model] = body
        return out
    check_container(doc, path)
    model = doc.get("model")
    if not model:
        raise SystemExit(f"{path} is a single-model container but names no model")
    return {model: doc}


def container_coprocessor(body: dict, kind: str = "nrf", index: int = 0) -> dict | None:
    """One co-processor entry by (kind, index), or None. Routing only: the device
    takes kind/index from its own build config (see coproc_slot_t, boot_header.h)."""
    for entry in body.get("coprocessors", []):
        if entry.get("kind") == kind and entry.get("index", 0) == index:
            return entry
    return None


# Firmware variants (fw_variant_t, sec/boot_header.h) == vendor_fw_type_t.
FW_VARIANT_NONE = 0
FW_VARIANT_CUSTOM = 1
FW_VARIANT_UNIVERSAL = 2
FW_VARIANT_BITCOIN_ONLY = 3
FW_VARIANT_PRODTEST = 4

# Hardened codewords (FW_VARIANT_SEC_*, sec/boot_header.h): what the manifest's
# firmware_variant and the boot header's firmware_type carry. RM(1,5): every
# pair, INVALID included, is >= 16 bit flips apart.
FW_VARIANT_SEC_INVALID = 0x00000000
FW_VARIANT_SEC_NONE = 0xCCCCCCCC
FW_VARIANT_SEC_CUSTOM = 0x33333333
FW_VARIANT_SEC_UNIVERSAL = 0x5A5A5A5A
FW_VARIANT_SEC_BITCOIN_ONLY = 0xA5A5A5A5
FW_VARIANT_SEC_PRODTEST = 0x66666666

# small id -> codeword; the signer is the only place this direction is used.
FW_VARIANT_SEC = {
    FW_VARIANT_CUSTOM: FW_VARIANT_SEC_CUSTOM,
    FW_VARIANT_UNIVERSAL: FW_VARIANT_SEC_UNIVERSAL,
    FW_VARIANT_BITCOIN_ONLY: FW_VARIANT_SEC_BITCOIN_ONLY,
    FW_VARIANT_PRODTEST: FW_VARIANT_SEC_PRODTEST,
}

# Canonical variant names, keyed by the authenticated codeword. Must match
# Variant::name() / Variant::from_name in xtask's pq.rs.
FW_VARIANT_NAME = {
    FW_VARIANT_SEC_CUSTOM: "custom",
    FW_VARIANT_SEC_UNIVERSAL: "universal",
    FW_VARIANT_SEC_BITCOIN_ONLY: "btc-only",
    FW_VARIANT_SEC_PRODTEST: "prodtest",
}

# Module types (fw_module_type_t, sec/boot_header.h).
FW_MODULE_SECMON = 1
FW_MODULE_APP = 2
FW_MODULE_PRODTEST = 3

# firmware_manifest_entry_t.flags; BOOT marks the entry module (exactly one).
FW_MANIFEST_ENTRY_FLAG_BOOT = 0x1


def _sha256(b: bytes | bytearray) -> bytes:
    return hashlib.sha256(b).digest()


def _model_str(hw_model: int) -> str:
    """The hw_model u32 encodes 4 ASCII chars (e.g. 'T3W1')."""
    raw = hw_model.to_bytes(4, "little")
    text = raw.decode("ascii", "replace").rstrip("\x00")
    return text if text.isprintable() else f"0x{hw_model:08x}"


def boot_header_model_id(header: Any) -> str:
    """Model id from the boot header's authenticated hw_model (u32, Model, or bytes)."""
    hw = header.hw_model
    if isinstance(hw, int):
        return _model_str(hw)
    raw = hw if isinstance(hw, bytes) else bytes(hw.value)
    return raw.decode("ascii", "replace").rstrip("\x00")


# --- Variant manifest ("firmware directory") ---------------------------------
#
# Layout (little-endian), must byte-match the on-device manifest:
#   magic 'TRZD' | firmware_variant u32 | firmware_version[4]
#   | translations_root[32] | module_count u32 | entry[module_count]
#   entry: module_type u32 | flags u32 | addr u32 | chunk_size u32 | size u32
#          | code_hash[32]
# chunk_size precedes size+code_hash so the custom variant's zeroed-for-fold
# tail leaves it authenticated.

MANIFEST_MAGIC = b"TRZD"
_MANIFEST_FIXED = struct.Struct("<4sI4s32sI")
_MANIFEST_ENTRY = struct.Struct("<IIIII32s")
# firmware_manifest_proof_t: u32 node_count + nodes, right after the manifest,
# outside the variant leaf.
_PROOF_COUNT = struct.Struct("<I")
_ZERO32 = b"\x00" * 32
_ZERO4 = b"\x00" * 4

# Smart-hashing chain domain tags: 0x01 length-bound seed, 0x02 fold step.
CHAIN_SEED_TAG = pq_secure.CHAIN_SEED_TAG
CHAIN_STEP_TAG = pq_secure.CHAIN_STEP_TAG
# = FW_CHUNK_SIZE (manifest_header.S, *_pq.ld, boot_header.h). Per-module field;
# modules are not padded to it, so the last chunk may be partial. Must be
# <= IMAGE_CHUNK_SIZE and FLASH_BLOCK_SIZE-aligned for phase-2 streaming.
DEFAULT_CHUNK_SIZE = pq_secure.DEFAULT_CHUNK_SIZE


def module_code_hash(code: bytes | bytearray, chunk_size: int) -> bytes:
    """Smart-hashing chain code_hash; see trezorlib.firmware.pq_secure."""
    return pq_secure.module_code_hash(bytes(code), chunk_size)


def module_chain_intermediates(code: bytes | bytearray, chunk_size: int) -> list[bytes]:
    """Intermediate chain hashes for chunks 0 .. n-2, in consumption order."""
    return pq_secure.module_chain_intermediates(bytes(code), chunk_size)


def build_manifest(
    firmware_variant: int,
    entries: list[dict],
    translations_root: bytes = _ZERO32,
    firmware_version: bytes = _ZERO4,
) -> bytes:
    """Serialize a manifest. `firmware_variant` is the FW_VARIANT_SEC_* codeword;
    entries carry module_type, flags, addr, chunk_size, size, code_hash."""
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
            e.get("chunk_size", DEFAULT_CHUNK_SIZE),
            e["size"],
            e["code_hash"],
        )
    return buf


def read_manifest(fw: bytes | bytearray) -> bytes:
    """The manifest bytes at the image start (what the variant leaf hashes)."""
    magic, _v, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("no manifest at the firmware image start")
    return bytes(fw[0 : _MANIFEST_FIXED.size + mc * _MANIFEST_ENTRY.size])


def _manifest_len(fw: bytes | bytearray) -> int:
    """Byte length of the manifest; the proof begins right after it."""
    magic, _v, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("no manifest at the firmware image start")
    return _MANIFEST_FIXED.size + mc * _MANIFEST_ENTRY.size


def build_manifest_proof(proof_nodes: list[bytes]) -> bytes:
    """Serialize firmware_manifest_proof_t (empty proof = zero count)."""
    if len(proof_nodes) > FW_MANIFEST_PROOF_MAX_NODES:
        raise ValueError(
            f"proof {len(proof_nodes)} > {FW_MANIFEST_PROOF_MAX_NODES} nodes"
        )
    return _PROOF_COUNT.pack(len(proof_nodes)) + b"".join(proof_nodes)


def read_manifest_proof(fw: bytes | bytearray) -> list[bytes]:
    """The embedded proof nodes following the manifest."""
    off = _manifest_len(fw)
    (count,) = _PROOF_COUNT.unpack_from(fw, off)
    if count > FW_MANIFEST_PROOF_MAX_NODES:
        raise ValueError(f"proof node_count {count} > {FW_MANIFEST_PROOF_MAX_NODES}")
    off += _PROOF_COUNT.size
    return [bytes(fw[off + i * 32 : off + i * 32 + 32]) for i in range(count)]


def read_manifest_region(fw: bytes | bytearray) -> bytes:
    """[manifest || proof struct]: the FirmwareBegin preamble bytes."""
    off = _manifest_len(fw)
    (count,) = _PROOF_COUNT.unpack_from(fw, off)
    if count > FW_MANIFEST_PROOF_MAX_NODES:
        raise ValueError(f"proof node_count {count} > {FW_MANIFEST_PROOF_MAX_NODES}")
    return bytes(fw[0 : off + _PROOF_COUNT.size + count * 32])


def install_manifest_proof(fw: bytearray, proof_nodes: list[bytes]) -> bytearray:
    """Bake the proof into the manifest region in place (fits FW_MANIFEST_REGION)."""
    off = _manifest_len(fw)
    blob = build_manifest_proof(proof_nodes)
    if off + len(blob) > FW_MANIFEST_REGION:
        raise ValueError(
            f"manifest ({off} B) + proof ({len(blob)} B) exceeds "
            f"FW_MANIFEST_REGION ({FW_MANIFEST_REGION} B)"
        )
    fw[off : off + len(blob)] = blob
    return fw


def manifest_entries(fw: bytes | bytearray) -> list[dict]:
    """Parse the manifest directory into entry dicts, in manifest order."""
    magic, _v, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError("no manifest at the firmware image start")
    entries = []
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        mtype, flags, addr, chunk_size, size, code_hash = _MANIFEST_ENTRY.unpack_from(
            fw, eoff
        )
        entries.append(
            {
                "module_type": mtype,
                "flags": flags,
                "addr": addr,
                "chunk_size": chunk_size,
                "size": size,
                "code_hash": code_hash,
            }
        )
    return entries


def format_manifest(manifest: bytes) -> str:
    """Human-readable dump of a manifest."""
    magic, variant, ver, tr_root, mc = _MANIFEST_FIXED.unpack_from(manifest, 0)
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
        mtype, flags, addr, cs, size, ch = _MANIFEST_ENTRY.unpack_from(manifest, eoff)
        tname = TYPE_NAMES.get(mtype, f"type{mtype}")
        ch_s = "ZEROED (custom/wildcard)" if not any(ch) else bytes(ch).hex()
        boot = " BOOT" if flags & FW_MANIFEST_ENTRY_FLAG_BOOT else ""
        lines.append(
            f"  [{i}] {tname:14} flags 0x{flags:x}{boot} addr 0x{addr:06x} "
            f"chunk {cs} size {size:>8}  code_hash {ch_s}"
        )
    return "\n".join(lines)


def manifest_variant(manifest: bytes) -> int:
    """The manifest's firmware_variant (a FW_VARIANT_SEC_* codeword)."""
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


def build_chunk_prev_hashes(fw: bytes | bytearray) -> dict[int, bytes]:
    """Map each outer chunk's END offset -> its chain H_prev (FirmwareUpload.prev_hash).

    Keyed by end offset so `request.offset + request.length` looks it up. The
    innermost chunk has no entry (the device derives the seed).
    """
    out: dict[int, bytes] = {}
    for e in manifest_entries(fw):
        cs = e["chunk_size"]
        code = bytes(fw[e["addr"] : e["addr"] + e["size"]])
        for k, h in enumerate(module_chain_intermediates(code, cs)):
            out[e["addr"] + (k + 1) * cs] = h  # keyed by the chunk's END offset
    return out


def is_custom_firmware(fw: bytes | bytearray) -> bool:
    """True iff the firmware's authenticated variant is CUSTOM."""
    try:
        return manifest_variant(read_manifest(fw)) == FW_VARIANT_SEC_CUSTOM
    except ValueError:
        return False


def fill_manifest(fw: bytearray) -> bytearray:
    """Fill each entry's code_hash in the compile-time manifest template in place.

    Always the real hash, including a CUSTOM variant's app: the founder-zeroing
    happens only in the authenticity fold (variant_leaf), never on flash.
    """
    magic, _variant, _ver, _tr, mc = _MANIFEST_FIXED.unpack_from(fw, 0)
    if magic != MANIFEST_MAGIC:
        raise ValueError(
            "no manifest template at the image start (manifest_header.S missing?)"
        )
    for i in range(mc):
        eoff = _MANIFEST_FIXED.size + i * _MANIFEST_ENTRY.size
        # code_hash is at entry offset +20 (after type, flags, addr, chunk_size, size).
        _mtype, _flags, addr, chunk_size, size, _ch = _MANIFEST_ENTRY.unpack_from(
            fw, eoff
        )
        code = bytes(fw[addr : addr + size])
        fw[eoff + 20 : eoff + 52] = module_code_hash(code, chunk_size)
    return fw


def authenticity_manifest(manifest: bytes) -> bytes:
    """The manifest bytes the variant leaf hashes (custom-zeroed)."""
    return pq_secure.authenticity_bytes(manifest)


def variant_leaf(manifest: bytes) -> bytes:
    """The variant's Merkle leaf: H(0x00 || authenticity_manifest)."""
    return pq_secure.variant_leaf(manifest)


# --- Founder (multi-variant) firmware_root -----------------------------------
#
# The founder level combines variant leaves AS NODE HASHES (sorted-pair
# internal_hash), not re-leaf-hashed: the device folds its variant leaf directly.


class _PreHashedLeaf:
    """A leaf whose tree_hash is a precomputed variant leaf; duck-types NodeType."""

    def __init__(self, node_hash: bytes) -> None:
        self.tree_hash = node_hash
        self.proof: list[bytes] = []

    def add_to_proof_list(self, proof_entry: bytes) -> None:
        self.proof.append(proof_entry)


def _fold_proof(node: bytes, proof: list[bytes]) -> bytes:
    """Fold a variant leaf to firmware_root as the device does (sorted-pair)."""
    for sibling in proof:
        node = merkle_tree.internal_hash(node, sibling)
    return node


def build_founder_tree(
    variant_leaves: list[bytes],
) -> tuple[bytes, dict[bytes, list[bytes]]]:
    """Return (firmware_root, {variant_leaf: proof}); leaves must be distinct."""
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
    for r, proof in proofs.items():
        assert _fold_proof(r, proof) == root, "founder-tree proof mismatch"
    return root, proofs


def firmware_root_multi(
    variant_images: dict[str, bytes],
) -> tuple[bytes, dict[str, tuple[bytes, list[bytes]]]]:
    """{variant_name: firmware.bin} -> (firmware_root, {name: (leaf, proof)})."""
    leaves = {
        name: variant_leaf(read_manifest(fw)) for name, fw in variant_images.items()
    }
    root, proofs = build_founder_tree(list(leaves.values()))
    return root, {name: (lf, proofs[lf]) for name, lf in leaves.items()}
