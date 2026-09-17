"""nRF firmware in the founder Merkle tree (pq_secure_boot).

The nRF image is a model-level leaf under the one boot-header signature:
leaf = H(0x00 || coproc_slot), slot = "TRZP" | model | kind | index | rsvd | image hash.
Fixed-depth tree, so every co-path is MODEL_TREE_DEPTH nodes; see
docs/core/embed-arch/firmware-merkle-tree.md.
"""

from __future__ import annotations

import hashlib
import struct

from trezorlib import merkle_tree
from trezorlib._internal import firmware_headers

# 2^4 = 16 leaf slots (~8 models x [STM, nRF]); raising it re-signs everything.
MODEL_TREE_DEPTH = 4
MODEL_TREE_LEAVES = 1 << MODEL_TREE_DEPTH

# --- MCUboot image parsing (mirrors io/nrf/stm32u5/nrf_update.c) -------------
IMAGE_MAGIC = 0x96F3B83D
TLV_INFO_MAGIC = 0x6907
TLV_PROT_INFO_MAGIC = 0x6908
TLV_MODEL_ID = 0x00A3  # custom TLV: 4-byte model tag, e.g. b"T3W1" (protected)
# Founder sigmask, PROTECTED (inside image hash and leaf); stamped by the signer.
TLV_SIGMASK = 0x00A2
# MCUboot security counter (protected); carries the boot header's monotonic_version.
TLV_SEC_CNT = 0x50

# Classic scheme: two Ed25519 signatures over the image hash, UNPROTECTED area.
LEGACY_TLV_SIG_0 = 0x00A0
LEGACY_TLV_SIG_1 = 0x00A1
LEGACY_SIG_LEN = 64

# PQ material (unprotected): founder signature over modelRoot + co-path. It
# depends on the leaf, so it cannot be inside it; record order carries no meaning.
PQ_TLV_FIRST = 0x00A4
PQ_TLV_LAST = 0x00A8
PQ_TLV_SLH_SIG_0 = 0x00A4  # SLH-DSA over modelRoot
PQ_TLV_SLH_SIG_1 = 0x00A5
PQ_TLV_EC_SIG_0 = 0x00A6  # Ed25519 over H(modelRoot || slh_sig)
PQ_TLV_EC_SIG_1 = 0x00A7
PQ_TLV_MERKLE_PROOF = 0x00A8  # leaf -> modelRoot ("co-path"), 32*N bytes
# Mirror BOOT_HEADER_PQ/EC_SIGNATURE_LEN (SPHINCS+-SHA2-128s / Ed25519).
PQ_SLH_SIG_LEN = 7856
PQ_EC_SIG_LEN = 64

# ih_magic, ih_load_addr, ih_hdr_size, ih_protect_tlv_size, ih_img_size, ih_flags,
# ih_ver{major,minor,revision,build_num}, _pad1
_MCUBOOT_HDR = struct.Struct("<IIHHIIBBHII")
_NODE = 32
_PROOF_COUNT = struct.Struct("<I")


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _tlv_areas(image: bytes) -> list[tuple[int, int]]:
    """Return (start, end) byte ranges of the protected then unprotected TLV areas."""
    magic, _load, hdr, prot, imgsz, _flags, _a, _b, _c, _d, _pad = (
        _MCUBOOT_HDR.unpack_from(image)
    )
    if magic != IMAGE_MAGIC:
        raise ValueError("not an MCUboot image (bad magic)")
    areas = []
    prot_off = hdr + imgsz
    if prot > 0:  # protected TLV area includes its own 4-byte info header
        areas.append((prot_off + 4, prot_off + prot))
    unprot_off = prot_off + prot
    if unprot_off + 4 <= len(image):
        info_magic, info_len = struct.unpack_from("<HH", image, unprot_off)
        if info_magic == TLV_INFO_MAGIC:
            areas.append((unprot_off + 4, unprot_off + info_len))
    return areas


def mcuboot_find_prot_tlv(image: bytes, tlv_type: int) -> bytes | None:
    """Find a TLV in the PROTECTED area only (mirrors nrf_image_find_prot_tlv);
    an unprotected copy is outside the image hash and must never be accepted."""
    areas = _tlv_areas(image)
    if not areas:
        return None
    start, end = areas[0]  # protected first, by construction
    p = start
    while p + 4 <= end:
        t, ln = struct.unpack_from("<HH", image, p)
        if t == tlv_type:
            return image[p + 4 : p + 4 + ln]
        p += 4 + ln
    return None


def mcuboot_find_tlv(image: bytes, tlv_type: int) -> bytes | None:
    for start, end in _tlv_areas(image):
        p = start
        while p + 4 <= end:
            t, ln = struct.unpack_from("<HH", image, p)
            if t == tlv_type:
                return image[p + 4 : p + 4 + ln]
            p += 4 + ln
    return None


def mcuboot_model_id(image: bytes) -> bytes:
    v = mcuboot_find_tlv(image, TLV_MODEL_ID)
    if v is None:
        raise ValueError(f"MCUboot image has no model-id TLV (0x{TLV_MODEL_ID:04x})")
    return v


def mcuboot_version(image: bytes) -> tuple[int, int, int, int]:
    _m, _l, _h, _p, _i, _f, major, minor, rev, build, _pad = _MCUBOOT_HDR.unpack_from(
        image
    )
    return (major, minor, rev, build)


# --- founder tree ------------------------------------------------------------


def mcuboot_prot_end(image: bytes | bytearray) -> int:
    """End of MCUboot's hashed region (hdr + payload + protected TLVs)."""
    if len(image) < _MCUBOOT_HDR.size:
        raise ValueError("truncated MCUboot image")
    magic, _load, hdr, prot, imgsz, *_rest = _MCUBOOT_HDR.unpack_from(image)
    if magic != IMAGE_MAGIC:
        raise ValueError("not an MCUboot image (bad magic)")
    prot_end = hdr + imgsz + prot
    if hdr < _MCUBOOT_HDR.size or prot_end > len(image):
        raise ValueError(
            f"malformed MCUboot image: protected region {prot_end} B "
            f"(hdr {hdr} + img {imgsz} + prot {prot}) vs image {len(image)} B"
        )
    return prot_end


def pq_material_offset(image: bytes) -> int | None:
    """Offset of the first founder TLV record, or None (classic image)."""
    prot_end = mcuboot_prot_end(image)
    if prot_end + 4 > len(image):
        return None
    info_magic, info_len = struct.unpack_from("<HH", image, prot_end)
    if info_magic != TLV_INFO_MAGIC:
        return None
    end = min(prot_end + info_len, len(image))
    p = prot_end + 4
    while p + 4 <= end:
        t, ln = struct.unpack_from("<HH", image, p)
        if p + 4 + ln > end:
            return None  # malformed record; nothing founder-ish found before it
        if PQ_TLV_FIRST <= t <= PQ_TLV_LAST:
            return p
        p += 4 + ln
    return None


def has_pq_material(image: bytes) -> bool:
    """True iff the image carries founder material (i.e. is PQ-native)."""
    return pq_material_offset(image) is not None


# Co-processor slot -- mirrors coproc_slot_t in sec/image/inc/sec/boot_header.h
# and the same struct in mcuboot's image_pq.c. 44 bytes:
#   tag(4) | model(4) | kind(1) | index(1) | reserved(2) | digest(32)
COPROC_SLOT_TAG = b"TRZP"
COPROC_KIND_NRF = 1
_COPROC_SLOT = struct.Struct("<4s4sBB2x32s")


def coproc_slot_value(model_id: bytes, kind: int, index: int, digest: bytes) -> bytes:
    """A co-processor's role-bound slot value. The sorted-pair fold discards
    position, so the role lives in the value; kind/index come from the caller's
    build config, never from the image or the wire."""
    if len(model_id) != 4:
        raise ValueError(f"model_id must be 4 bytes, got {len(model_id)!r}")
    if len(digest) != 32:
        raise ValueError(f"digest must be 32 bytes, got {len(digest)}")
    if not 0 <= kind <= 0xFF or not 0 <= index <= 0xFF:
        raise ValueError("kind and index are single bytes")
    value = _COPROC_SLOT.pack(COPROC_SLOT_TAG, model_id, kind, index, digest)
    assert len(value) == 44, len(value)
    return value


def nrf_leaf_value(image: bytes, index: int = 0) -> bytes:
    """The nRF's slot value: a coproc slot over MCUboot's image hash (TLV 0x10 range).

    Model id is read from the image because this is the signer; a verifier takes
    it from its build config. Pass this, never the raw image, to build_model_tree.
    """
    model_id = mcuboot_model_id(image)
    if model_id is None:
        raise ValueError("nRF image has no MCUboot model-id TLV")
    return coproc_slot_value(
        model_id, COPROC_KIND_NRF, index, mcuboot_image_hash(image)
    )


def nrf_leaf(image: bytes) -> bytes:
    """The nRF's leaf = H(0x00 || nrf_leaf_value(image)), not the bare image hash."""
    return merkle_tree.leaf_hash(nrf_leaf_value(image))


def _placeholder_slot(i: int) -> bytes:
    return b"pq_secure_boot:model-tree-pad:" + struct.pack("<H", i)


def build_model_tree(slot_values: list[bytes]) -> tuple[bytes, list[list[bytes]]]:
    """Fixed-depth tree over slot VALUES, padded to 2^MODEL_TREE_DEPTH.
    Returns (modelRoot, proofs) with a MODEL_TREE_DEPTH-node co-path per value."""
    if len(slot_values) > MODEL_TREE_LEAVES:
        raise ValueError(
            f"{len(slot_values)} slots > {MODEL_TREE_LEAVES} (raise MODEL_TREE_DEPTH)"
        )
    # A raw MCUboot image passed as a slot value would silently build a wrong leaf.
    for i, v in enumerate(slot_values):
        if len(v) >= _MCUBOOT_HDR.size and v[:4] == struct.pack("<I", IMAGE_MAGIC):
            raise ValueError(
                f"slot {i}: pass nrf_leaf_value(image) (its 32-byte MCUboot image "
                f"hash), not the raw {len(v)} B image"
            )
    padded = list(slot_values) + [
        _placeholder_slot(i) for i in range(len(slot_values), MODEL_TREE_LEAVES)
    ]
    tree = merkle_tree.MerkleTree(padded)
    proofs = [tree.get_proof(v) for v in slot_values]
    for p in proofs:
        assert len(p) == MODEL_TREE_DEPTH, (len(p), MODEL_TREE_DEPTH)
    return tree.get_root_hash(), proofs


def _refit_auth_padding(bl: firmware_headers.BootloaderV2Image) -> None:
    """Re-fit the authenticated padding after the model path changed size."""
    bl.header.padding = b"\x00" * (bl.header.auth_len - bl.header._pre_padding_len)


def model_leaf_value(bl: firmware_headers.BootloaderV2Image) -> bytes:
    """Size the model path to MODEL_TREE_DEPTH nodes and return the stable model leaf value."""
    bl.set_merkle_proof([b"\x00" * _NODE] * MODEL_TREE_DEPTH)
    _refit_auth_padding(bl)
    return bl._leaf_value()


def place_bootloader_in_tree(
    bl: firmware_headers.BootloaderV2Image, model_copath: list[bytes]
) -> None:
    """Seat the boot header in the model tree without signing (prepare-then-sign)."""
    if len(model_copath) != MODEL_TREE_DEPTH:
        raise ValueError("model co-path length must equal MODEL_TREE_DEPTH")
    bl.set_merkle_proof(model_copath)
    _refit_auth_padding(bl)


# --- OTA artifact + verification --------------------------------------------


# --- Test-only OTA container ------------------------------------------------
#
# NOT a wire format: the device gets co-path and image as separate FirmwareBegin
# fields. Used by gen_nrf_vector.py and the self-test only.


def build_nrf_ota(image: bytes, co_path: list[bytes]) -> bytes:
    """OTA payload: proof_count || co_path nodes || mcuboot_image."""
    return _PROOF_COUNT.pack(len(co_path)) + b"".join(co_path) + image


def parse_nrf_ota(artifact: bytes) -> tuple[list[bytes], bytes]:
    (count,) = _PROOF_COUNT.unpack_from(artifact, 0)
    off = _PROOF_COUNT.size
    co_path = [artifact[off + i * _NODE : off + (i + 1) * _NODE] for i in range(count)]
    off += count * _NODE
    return co_path, artifact[off:]


def verify_nrf_ota(model_root: bytes, artifact: bytes, device_model_id: bytes) -> dict:
    """Host mirror of the device install check: the slot over the MCUboot image
    hash folds through the co-path to modelRoot, and the model-id TLV matches."""
    co_path, image = parse_nrf_ota(artifact)
    if merkle_tree.evaluate_proof(nrf_leaf_value(image), co_path) != model_root:
        raise ValueError("nRF image leaf + co-path does not fold to modelRoot")
    model_id = mcuboot_model_id(image)
    if model_id != device_model_id:
        raise ValueError(f"nRF model id {model_id!r} != device {device_model_id!r}")
    return {
        "model_id": model_id,
        "version": mcuboot_version(image),
        "image_size": len(image),
    }


# --- demo -------------------------------------------------------------------


def _fake_mcuboot_image(model_tag: bytes, body: bytes, founder: bool = False) -> bytes:
    """Minimal MCUboot image with the exact record set the shape whitelist expects.

    PROTECTED    0x00A2 sigmask (1 B), 0x00A3 model id (4 B)
    UNPROTECTED  0x0010 image hash, then classic 0x00A0+0x00A1 or founder 0x00A4..0x00A8
    """
    hdr_size, imgsz = 32, len(body)
    # sigmask 0x03 for classic (as build_sign_flash.sh); 0x00 placeholder for founder.
    prot_tlvs = struct.pack("<HH", TLV_SIGMASK, 1) + bytes([0x00 if founder else 0x03])
    prot_tlvs += struct.pack("<HH", TLV_MODEL_ID, 4) + model_tag
    prot_area = struct.pack("<HH", TLV_PROT_INFO_MAGIC, 4 + len(prot_tlvs)) + prot_tlvs
    header = _MCUBOOT_HDR.pack(
        IMAGE_MAGIC, 0, hdr_size, len(prot_area), imgsz, 0, 9, 9, 9, 9, 0
    )
    # The 0x10 TLV must carry the real hash; the leaf is built over it.
    covered = header + b"\x00" * (hdr_size - _MCUBOOT_HDR.size) + body + prot_area
    unprot_tlvs = struct.pack("<HH", MCUBOOT_TLV_SHA256, 32) + _sha256(covered)
    if not founder:
        # Placeholder values; only the shape is exercised here.
        unprot_tlvs += (
            struct.pack("<HH", LEGACY_TLV_SIG_0, LEGACY_SIG_LEN)
            + b"\xab" * LEGACY_SIG_LEN
        )
        unprot_tlvs += (
            struct.pack("<HH", LEGACY_TLV_SIG_1, LEGACY_SIG_LEN)
            + b"\xcd" * LEGACY_SIG_LEN
        )
    if founder:
        # Real sizes, last in the area, no slack.
        for t, ln in (
            (PQ_TLV_SLH_SIG_0, PQ_SLH_SIG_LEN),
            (PQ_TLV_SLH_SIG_1, PQ_SLH_SIG_LEN),
            (PQ_TLV_EC_SIG_0, PQ_EC_SIG_LEN),
            (PQ_TLV_EC_SIG_1, PQ_EC_SIG_LEN),
            (PQ_TLV_MERKLE_PROOF, MODEL_TREE_DEPTH * 32),
        ):
            unprot_tlvs += struct.pack("<HH", t, ln) + bytes([t & 0xFF]) * ln
    unprot_area = struct.pack("<HH", TLV_INFO_MAGIC, 4 + len(unprot_tlvs)) + unprot_tlvs
    return (
        header
        + b"\x00" * (hdr_size - _MCUBOOT_HDR.size)
        + body
        + prot_area
        + unprot_area
    )


def _pq_record_sizes() -> list[tuple[int, int]]:
    """(type, value_len) of the founder records, in the order they are appended."""
    return [
        (PQ_TLV_SLH_SIG_0, PQ_SLH_SIG_LEN),
        (PQ_TLV_SLH_SIG_1, PQ_SLH_SIG_LEN),
        (PQ_TLV_EC_SIG_0, PQ_EC_SIG_LEN),
        (PQ_TLV_EC_SIG_1, PQ_EC_SIG_LEN),
        (PQ_TLV_MERKLE_PROOF, MODEL_TREE_DEPTH * 32),
    ]


MCUBOOT_TLV_SHA256 = 0x10


def mcuboot_image_hash(image: bytes) -> bytes:
    """MCUboot's image hash: SHA-256 over hdr + payload + protected TLVs (TLV 0x10)."""
    return _sha256(image[: mcuboot_prot_end(image)])


def _patch_protected_tlv(image: bytes, tlv_type: int, value: bytes, what: str) -> bytes:
    """Overwrite a PROTECTED TLV's value in place and re-stamp TLV 0x10.

    The record must already exist at the right size (build emits a placeholder).
    Call before the leaf is computed: protected TLVs are inside the leaf.
    """
    out = bytearray(image)
    magic, _load, hdr, prot, imgsz, *_rest = _MCUBOOT_HDR.unpack_from(out)
    if magic != IMAGE_MAGIC:
        raise ValueError("not an MCUboot image (bad magic)")
    if prot == 0:
        raise ValueError(f"image has no protected TLV area to hold the {what}")

    # Protected area only; an unprotected same-typed record is not in the leaf.
    prot_off = hdr + imgsz
    p, end = prot_off + 4, prot_off + prot
    while p + 4 <= end:
        t, ln = struct.unpack_from("<HH", out, p)
        if t == tlv_type:
            if ln != len(value):
                raise ValueError(
                    f"protected {what} TLV has length {ln}, expected {len(value)}"
                )
            out[p + 4 : p + 4 + ln] = value
            break
        p += 4 + ln
    else:
        raise ValueError(
            f"no protected {what} TLV (0x{tlv_type:04x}); the nRF image must be "
            "built with a placeholder for the signer to fill"
        )

    # Re-stamp MCUboot's image hash over the modified protected region.
    digest = mcuboot_image_hash(bytes(out))
    info_magic, info_len = struct.unpack_from("<HH", out, prot_off + prot)
    if info_magic != TLV_INFO_MAGIC:
        raise ValueError("image has no unprotected TLV area (no image-hash TLV)")
    hp = prot_off + prot + 4
    hend = min(prot_off + prot + info_len, len(out))
    while hp + 4 <= hend:
        t, ln = struct.unpack_from("<HH", out, hp)
        if t == MCUBOOT_TLV_SHA256:
            if ln != len(digest):
                raise ValueError(f"image-hash TLV has length {ln}")
            out[hp + 4 : hp + 4 + ln] = digest
            break
        hp += 4 + ln
    else:
        raise ValueError(f"no image-hash TLV (0x{MCUBOOT_TLV_SHA256:04x}) to re-stamp")

    return bytes(out)


def set_protected_sigmask(image: bytes, sigmask: int) -> bytes:
    """Write the founder `sigmask` into the PROTECTED sigmask TLV (signer-owned;
    set value -> compute leaf -> sign, as with the boot header's sigmask)."""
    if not 0 <= sigmask <= 0xFF:
        raise ValueError(f"sigmask {sigmask} out of range")
    return _patch_protected_tlv(image, TLV_SIGMASK, bytes([sigmask]), "sigmask")


def set_protected_monotonic(image: bytes, monotonic_version: int) -> bytes:
    """Write the boot header's `monotonic_version` into the PROTECTED security
    counter TLV, so STM and nRF share one anti-rollback axis
    (CONFIG_BOOT_PQ_ROLLBACK_PROT)."""
    # MONOCTR_MAX_VALUE (sec/monoctr.h): the STM's unary monoctr bounds the axis.
    if not 0 <= monotonic_version <= 63:
        raise ValueError(
            f"monotonic_version {monotonic_version} exceeds MONOCTR_MAX_VALUE (63), "
            "the STM's unary monoctr ceiling for the shared anti-rollback axis"
        )
    return _patch_protected_tlv(
        image, TLV_SEC_CNT, struct.pack("<I", monotonic_version), "security counter"
    )


def add_pq_placeholders(image: bytes) -> bytes:
    """Append zeroed founder records to the unprotected TLV area (PQ-native image).

    Record SIZES are inside the leaf, contents come after signing: hence
    add_pq_placeholders() -> build tree -> sign -> fill_pq_material().
    """
    magic, _load, hdr, prot, imgsz, *_rest = _MCUBOOT_HDR.unpack_from(image)
    if magic != IMAGE_MAGIC:
        raise ValueError("not an MCUboot image (bad magic)")
    if has_pq_material(image):
        raise ValueError("image already carries founder material")

    prot_end = hdr + imgsz + prot
    info_magic, info_len = struct.unpack_from("<HH", image, prot_end)
    if info_magic != TLV_INFO_MAGIC:
        raise ValueError("image has no unprotected TLV area to extend")
    area_end = prot_end + info_len
    if area_end > len(image):
        raise ValueError("unprotected TLV area overruns the image")

    records = b"".join(
        struct.pack("<HH", t, ln) + bytes(ln) for t, ln in _pq_record_sizes()
    )
    new_info_len = info_len + len(records)
    if new_info_len > 0xFFFF:
        raise ValueError(f"unprotected TLV area would exceed 16 bits ({new_info_len})")

    out = bytearray(image[:area_end])
    struct.pack_into("<HH", out, prot_end, TLV_INFO_MAGIC, new_info_len)
    out += records
    # Trailing padding is dropped; the bundle re-pads for flash alignment.
    return bytes(out)


def fill_pq_material(
    image: bytes, slh_sigs: list[bytes], ec_sigs: list[bytes], co_path: list[bytes]
) -> bytes:
    """Write the founder signatures + co-path into the placeholders (leaf unchanged)."""
    expect = _pq_record_sizes()
    values = [slh_sigs[0], slh_sigs[1], ec_sigs[0], ec_sigs[1], b"".join(co_path)]

    cut = pq_material_offset(image)
    if cut is None:
        raise ValueError("image has no founder placeholders (call add_* first)")

    out = bytearray(image)
    p = cut
    for (t, ln), val in zip(expect, values):
        got_t, got_ln = struct.unpack_from("<HH", out, p)
        if (got_t, got_ln) != (t, ln):
            raise ValueError(
                f"founder record mismatch at {p}: expected 0x{t:04x}/{ln}, "
                f"found 0x{got_t:04x}/{got_ln}"
            )
        if len(val) != ln:
            raise ValueError(f"value for 0x{t:04x} is {len(val)} B, expected {ln}")
        out[p + 4 : p + 4 + ln] = val
        p += 4 + ln
    if p != len(out):
        raise ValueError(f"founder records end at {p}, image is {len(out)} B (slack)")

    filled = bytes(out)
    assert nrf_leaf(filled) == nrf_leaf(image), (
        "filling founder material moved the leaf"
    )
    return filled


# --- classic (legacy) signing, for test fixtures only ---------------------------


def legacy_key_slots(sigmask: int, key_count: int) -> tuple[int, int] | None:
    """Which pool keys the sigmask names, or None if not a legal 2-of-3 selection.
    Mirrors nrf_image_legacy_sig_slots() in io/nrf/nrf_image.c and MCUboot; NOT
    the founder scheme's i-th-lowest-set-bit rule."""
    if bin(sigmask).count("1") != 2 or (sigmask & ~0x07) != 0:
        return None
    i0 = 0 if (sigmask & 0x01) else 1
    i1 = 2 if (sigmask & 0x04) else 1
    if i0 == i1 or i0 >= key_count or i1 >= key_count:
        return None
    return (i0, i1)


def legacy_sign(image: bytes, secret_keys: list[bytes], sigmask: int) -> bytes:
    """Sign a CLASSIC fixture image: two Ed25519 records over the MCUboot image
    hash, keys selected by the protected sigmask. Production images are signed
    by nordic/trezor/scripts/insert_signatures.py."""
    from trezorlib import _ed25519

    image = set_protected_sigmask(image, sigmask)  # protected -> changes the hash
    slots = legacy_key_slots(sigmask, len(secret_keys))
    if slots is None:
        raise ValueError(f"sigmask 0x{sigmask:02x} is not a legal 2-of-3 selection")
    digest = mcuboot_image_hash(image)
    out = bytearray(image)
    for tlv, idx in zip((LEGACY_TLV_SIG_0, LEGACY_TLV_SIG_1), slots):
        sk = secret_keys[idx]
        sig = _ed25519.signature_unsafe(digest, sk, _ed25519.publickey_unsafe(sk))
        assert len(sig) == LEGACY_SIG_LEN
        off = _find_unprot_tlv_offset(out, tlv)
        out[off + 4 : off + 4 + LEGACY_SIG_LEN] = sig
    return bytes(out)


def _find_unprot_tlv_offset(image: bytes | bytearray, want: int) -> int:
    """Byte offset of a record's header in the UNPROTECTED area. Raises if absent."""
    prot_end = mcuboot_prot_end(image)
    info_magic, info_len = struct.unpack_from("<HH", image, prot_end)
    if info_magic != TLV_INFO_MAGIC:
        raise ValueError("image has no unprotected TLV area")
    end = min(prot_end + info_len, len(image))
    p = prot_end + 4
    while p + 4 <= end:
        t, ln = struct.unpack_from("<HH", image, p)
        if t == want:
            return p
        p += 4 + ln
    raise ValueError(f"no unprotected TLV 0x{want:04x}")


def corrupt_hash_tlv(image: bytes) -> bytes:
    """Adversarial fixture: flip a byte of the UNPROTECTED 0x10 hash record.
    The fold and shape check still pass; only recomputing the hash catches it."""
    prot_end = mcuboot_prot_end(image)
    out = bytearray(image)
    for start, end in _tlv_areas(image):
        if start < prot_end:
            continue  # protected area: a flip there would move the leaf
        q = start
        while q + 4 <= end:
            t, ln = struct.unpack_from("<HH", image, q)
            if t == MCUBOOT_TLV_SHA256:
                out[q + 4] ^= 0xFF
                return bytes(out)
            q += 4 + ln
    raise ValueError("no unprotected 0x10 record to corrupt")


def smuggle_rogue_tlv(image: bytes) -> bytes:
    """Adversarial fixture: split an unprotected record into a shorter one plus a
    rogue TLV of the same total size. Leaf and signatures still verify; only the
    per-scheme shape whitelist catches it."""
    cut = pq_material_offset(image)
    if cut is None:
        # Classic image: split its first signature record (above prot_end).
        prot_end = mcuboot_prot_end(image)
        for start, end in _tlv_areas(image):
            if start < prot_end:
                continue  # protected area
            q = start
            while q + 4 <= end and cut is None:
                t, ln = struct.unpack_from("<HH", image, q)
                if t == LEGACY_TLV_SIG_0:
                    cut = q
                q += 4 + ln
            if cut is not None:
                break
        if cut is None:
            raise ValueError("image has no record to split in the unprotected area")
    t, ln = struct.unpack_from("<HH", image, cut)
    total = 4 + ln
    keep = ln // 2
    rogue_len = total - (4 + keep) - 4
    if rogue_len < 0:
        raise ValueError("record too small to split")
    out = bytearray(image)
    struct.pack_into("<HH", out, cut, t, keep)
    struct.pack_into("<HH", out, cut + 4 + keep, 0x00B0, rogue_len)  # rogue type
    return bytes(out)


def _demo(bl_path: str, img_path: str) -> None:
    image = open(img_path, "rb").read()
    bl = firmware_headers.BootloaderV2Image.parse(open(bl_path, "rb").read())
    hw_model = bl.header.hw_model
    my_model = hw_model if isinstance(hw_model, bytes) else bytes(hw_model.value)

    other_model_leaf = _sha256(b"stand-in-other-model-boot-header")
    other_image = _fake_mcuboot_image(b"T3T2", b"other-nrf-body" * 500)

    pq_image = _fake_mcuboot_image(my_model, b"pq-native-nrf-body" * 400, founder=True)

    model_val = model_leaf_value(bl)  # sizes the model path, then reads the stable leaf
    # Slot values are nrf_leaf_value(image), never the raw image.
    slots = [
        model_val,
        nrf_leaf_value(image),
        other_model_leaf,
        nrf_leaf_value(other_image),  # [A-STM, A-nRF, B-STM, B-nRF]
        nrf_leaf_value(pq_image),
    ]  # + a PQ-native shape (founder TLVs)
    model_root, proofs = build_model_tree(slots)

    place_bootloader_in_tree(bl, proofs[0])
    bl.sign_with_devkeys()
    assert bl.merkle_root() == model_root, "boot-header fold != modelRoot"
    bl.verify(dev_keys=True)  # the ONE signature, over modelRoot

    ota = build_nrf_ota(image, proofs[1])
    print(
        f"MODEL_TREE_DEPTH={MODEL_TREE_DEPTH} ({MODEL_TREE_LEAVES} slots); modelRoot {model_root.hex()[:16]}"
    )
    print(
        f"image model_id={mcuboot_model_id(image)!r} version={mcuboot_version(image)}"
        f"  hashed range {mcuboot_prot_end(image)}/{len(image)} B"
        " (leaf = H(0x00 || the role-bound slot over that hash))"
    )
    print(
        f"nRF OTA artifact: {len(ota)} B  (image {len(image)} B + {MODEL_TREE_DEPTH}-node co-path, no header)"
    )
    print("boot-header signature over modelRoot: OK (the only signature)")
    print("genuine nRF verify:", verify_nrf_ota(model_root, ota, my_model))

    def reject(name: str, art: bytes) -> bool:
        try:
            verify_nrf_ota(model_root, art, my_model)
            print(f"  !! FAIL: {name} ACCEPTED")
            return False
        except Exception as e:
            print(f"  reject {name}: {e}")
            return True

    def flip(art: bytes, off: int) -> bytes:
        b = bytearray(art)
        b[off] ^= 0xFF
        return bytes(b)

    img_off = _PROOF_COUNT.size + MODEL_TREE_DEPTH * _NODE

    ok = True
    # Classic image: tamper below prot_end is caught by the fold.
    ok &= reject(
        "flipped byte in the body", flip(ota, img_off + mcuboot_prot_end(image) // 2)
    )
    # Unprotected-area tamper still folds by design; the STM checks those
    # signatures itself before pushing (nrf_image_legacy_accept_ok).
    try:
        verify_nrf_ota(model_root, flip(ota, len(ota) - 1), my_model)
        print(
            "  (by design) classic unprotected-TLV tamper still folds -- the STM"
            " verifies those signatures itself before pushing"
        )
    except Exception as e:  # noqa: BLE001
        print(f"  !! FAIL: classic unprotected tamper broke the fold: {e}")
        ok = False

    # PQ-native image: same boundary; founder material is outside the leaf.
    pq_ota = build_nrf_ota(pq_image, proofs[4])
    print(
        f"PQ-native image: hashed range {mcuboot_prot_end(pq_image)}"
        f"/{len(pq_image)} B (founder material sits past it)"
    )
    print("  genuine PQ-native verify:", verify_nrf_ota(model_root, pq_ota, my_model))
    ok &= reject(
        "PQ-native, flipped byte inside the covered range",
        flip(pq_ota, img_off + mcuboot_prot_end(pq_image) // 2),
    )
    try:
        verify_nrf_ota(model_root, flip(pq_ota, len(pq_ota) - 1), my_model)
        print(
            "  (by design) PQ-native founder-material tamper still folds -- the STM"
            " must verify the founder material before pushing"
        )
    except Exception as e:  # noqa: BLE001
        print(f"  !! FAIL: founder-material tamper broke the fold: {e}")
        ok = False

    ok &= reject(
        "other model's nRF (folds OK, wrong model id)",
        build_nrf_ota(other_image, proofs[3]),
    )
    print("RESULT:", "ALL REJECTED, genuine OK" if ok else "SOMETHING LEAKED")


if __name__ == "__main__":
    import sys

    _demo(sys.argv[1], sys.argv[2])
