"""nRF firmware in the founder Merkle tree (pq_secure_boot).

The nRF (BLE co-processor) firmware is committed as a **model-level leaf** in the
founder tree, covered by the ONE existing boot-header signature -- there is no
separate nRF signature. On T3W1 the nRF's own MCUboot (Ed25519) is unchanged;
this layer is the STM-side founder gate that verifies an nRF image against the
signed tree before pushing it (raw) to the nRF over SMP serial recovery.

Leaf = H(0x00 || mcuboot_image): the leaf commits the MCUboot image **directly**,
so there is no separate nRF header to keep in sync -- the model id, version and
hash already live in the image (imgtool header + custom TLV 0x00A3 = model tag,
produced by nordic/trezor/scripts/build_sign_flash.sh). This is also forward-
compatible with future PQ-on-nRF: adding an SLH-DSA signature TLV to the image
just changes the committed bytes; the tree mechanism is unchanged.

Tree shape (prepared for MULTIPLE models), one signed root:

    modelRoot
    ├── <model A> STM leaf (its boot header) ├── <model A> nRF leaf = H(0x00 || A_image)
    ├── <model B> STM leaf                   ├── <model B> nRF leaf
    └── ... padded to 2^MODEL_TREE_DEPTH slots

Each STM boot header carries the co-path for its model leaf; each nRF image ships
its own co-path. The device folds nrf_leaf + co-path -> modelRoot.

FIXED DEPTH keeps every co-path MODEL_TREE_DEPTH nodes long, so the boot header's
auth padding (hence the model leaf) does not depend on how many models exist.

hw_model BINDING IS LOAD-BEARING: every model's nRF is under the same modelRoot,
so folding alone does not pin an image to a model -- another model's nRF folds
fine. The model id (TLV 0x00A3) read from the image and checked on-device is what
prevents a cross-model install.
"""

from __future__ import annotations

import hashlib
import struct

from trezorlib import merkle_tree
from trezorlib._internal import firmware_headers

# 2^4 = 16 leaf slots (~8 models x [STM leaf, nRF leaf]); raise (re-signs all) if exceeded.
MODEL_TREE_DEPTH = 4
MODEL_TREE_LEAVES = 1 << MODEL_TREE_DEPTH

# --- MCUboot image parsing (mirrors io/nrf/stm32u5/nrf_update.c) -------------
IMAGE_MAGIC = 0x96F3B83D
TLV_INFO_MAGIC = 0x6907
TLV_PROT_INFO_MAGIC = 0x6908
TLV_MODEL_ID = 0x00A3  # custom TLV: 4-byte model tag, e.g. b"T3W1" (protected)
# Which founder keys signed. PROTECTED (inside the image hash AND the leaf), shared
# with MCUboot's own EXPECTED_SIGMASK_TLV -- identical semantics. The SIGNER stamps
# it (set_protected_sigmask) before the leaf is computed, so the signature attests to
# the signer set without binding the binary to one key selection.
TLV_SIGMASK = 0x00A2

# The CLASSIC (non-founder) scheme's own signature records: two Ed25519 signatures
# over the image hash, in the UNPROTECTED area, inserted by insert_signatures.py
# after imgtool has laid the image out. The 2-of-3 key selection is named by the
# PROTECTED sigmask above, so both records always exist.
LEGACY_TLV_SIG_0 = 0x00A0
LEGACY_TLV_SIG_1 = 0x00A1
LEGACY_SIG_LEN = 64

# PQ material (unprotected): the founder signature over modelRoot + the Merkle
# proof. It depends on the leaf, so it cannot be covered by the leaf -- which is why
# it lives in the unprotected TLV area, outside MCUboot's image hash. Its position
# and order within that area carry no meaning: the leaf boundary is MCUboot's own
# (see nrf_leaf_value), not derived from these types. The records are contiguous
# only because the signer allocates them that way, and the shape check pins that.
PQ_TLV_FIRST = 0x00A4
PQ_TLV_LAST = 0x00A8
PQ_TLV_SLH_SIG_0 = 0x00A4  # SLH-DSA over modelRoot
PQ_TLV_SLH_SIG_1 = 0x00A5
PQ_TLV_EC_SIG_0 = 0x00A6  # Ed25519 over H(modelRoot || slh_sig)
PQ_TLV_EC_SIG_1 = 0x00A7
PQ_TLV_MERKLE_PROOF = 0x00A8  # leaf -> modelRoot ("co-path"), 32*N bytes
# Mirrors the STM's BOOT_HEADER_PQ/EC_SIGNATURE_LEN (SPHINCS+-SHA2-128s / Ed25519).
# NOTE: under the unified naming PQ is the SCHEME, so the halves are SLH and EC --
# the STM's *_PQ_SIGNATURE_LEN / *_PQ_KEYS still use PQ for the SLH half (deferred
# cleanup, see pq-tooling-integration-deferred).
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


def mcuboot_prot_end(image: bytes) -> int:
    """End of MCUboot's protected region: hdr + payload + protected TLVs.

    Exactly what the image hash -- hence the founder leaf -- covers. Everything at
    or past this offset is the unprotected TLV area, which no hash and no signature
    reaches; see nrf_leaf_value.
    """
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
    """Offset of the FIRST founder TLV record, or None if the image carries none.

    Only a locator for the signer's own placeholders -- it says nothing about the
    leaf, which is MCUboot's image hash regardless of what lives out here. A classic
    image returns None; a PQ-native one returns where its founder records begin.
    """
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


def nrf_leaf_value(image: bytes) -> bytes:
    """The nRF's model-tree SLOT VALUE: MCUboot's own image hash.

    The leaf commits the image THROUGH its MCUboot image hash (TLV 0x10's value:
    SHA-256 over header + payload + protected TLVs) rather than over a truncated
    byte range. That range is precisely "everything except the unprotected TLV
    area", which is the boundary the founder material needs -- it signs modelRoot,
    so it cannot lie inside its own preimage -- and MCUboot defines it rather than
    us deriving it from TLV types.

    Committing a collision-resistant hash commits the bytes, so nothing is
    weakened; and both verifiers already compute this hash for their own reasons,
    so neither has to hash the image twice.

    Pass THIS -- never the raw image -- to build_model_tree / get_proof /
    evaluate_proof, which all apply leaf_hash() to the value themselves.

    Being only 32 bytes, this value is also what lets a device check WHICH nRF a
    release expects without holding the image: fold H(0x00 || hash) through the
    co-path to modelRoot, then compare against the live chip's reported hash.
    """
    return mcuboot_image_hash(image)


def nrf_leaf(image: bytes) -> bytes:
    """The nRF's model-tree leaf = H(0x00 || mcuboot_image_hash(image))."""
    return merkle_tree.leaf_hash(nrf_leaf_value(image))


def _placeholder_slot(i: int) -> bytes:
    return b"pq_secure_boot:model-tree-pad:" + struct.pack("<H", i)


def build_model_tree(slot_values: list[bytes]) -> tuple[bytes, list[list[bytes]]]:
    """Fixed-depth model tree over the given leaf VALUES (model-leaf values and/or
    nRF images), padded to 2^MODEL_TREE_DEPTH slots. Returns (modelRoot, proofs)
    where proofs[i] is the MODEL_TREE_DEPTH-node co-path for slot_values[i]."""
    if len(slot_values) > MODEL_TREE_LEAVES:
        raise ValueError(
            f"{len(slot_values)} slots > {MODEL_TREE_LEAVES} (raise MODEL_TREE_DEPTH)"
        )
    # Guardrail: an nRF slot value must be nrf_leaf_value(image) -- a 32-byte
    # hash. MerkleTree hashes the value as given, so passing a raw image would
    # silently build a leaf over the wrong bytes and produce an image no verifier
    # accepts. An MCUboot magic at offset 0 is unambiguous evidence of that
    # mistake, whatever the image's shape.
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
    """Re-fit the maximized auth padding after the model-path length changed (the
    path length steals from the auth padding, which is authenticated -> changes the
    model leaf; fixed depth keeps it constant). Read the leaf only after this."""
    bl.header.padding = b"\x00" * (bl.header.auth_len - bl.header._pre_padding_len)


def model_leaf_value(bl: firmware_headers.BootloaderV2Image) -> bytes:
    """Size the model path to MODEL_TREE_DEPTH nodes and return the stable model leaf value."""
    bl.set_merkle_proof([b"\x00" * _NODE] * MODEL_TREE_DEPTH)
    _refit_auth_padding(bl)
    return bl._leaf_value()


def sign_bootloader_in_tree(
    bl: firmware_headers.BootloaderV2Image, model_copath: list[bytes]
) -> None:
    if len(model_copath) != MODEL_TREE_DEPTH:
        raise ValueError("model co-path length must equal MODEL_TREE_DEPTH")
    bl.set_merkle_proof(model_copath)
    _refit_auth_padding(bl)
    bl.sign_with_devkeys()


# --- OTA artifact + verification --------------------------------------------


def build_nrf_ota(image: bytes, co_path: list[bytes]) -> bytes:
    """OTA payload: proof_count || co_path nodes || mcuboot_image. The STM verifies
    it against modelRoot, then pushes the raw image to the nRF over SMP."""
    return _PROOF_COUNT.pack(len(co_path)) + b"".join(co_path) + image


def parse_nrf_ota(artifact: bytes) -> tuple[list[bytes], bytes]:
    (count,) = _PROOF_COUNT.unpack_from(artifact, 0)
    off = _PROOF_COUNT.size
    co_path = [artifact[off + i * _NODE : off + (i + 1) * _NODE] for i in range(count)]
    off += count * _NODE
    return co_path, artifact[off:]


def verify_nrf_ota(model_root: bytes, artifact: bytes, device_model_id: bytes) -> dict:
    """Host mirror of the device install check (no nRF signature):
    1. leaf = H(0x00 || founder-covered range) + co-path folds to the (verified)
       modelRoot -- the range excludes founder material, if any (see nrf_leaf),
    2. the image's model-id TLV matches THIS device (cross-model guard)."""
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
    """Minimal MCUboot image (header + protected model-id TLV + unprotected TLVs).

    Faithful to what the real signing flows emit, verified against a signed image:

      PROTECTED    0x00A2 sigmask (1 B), 0x00A3 model id (4 B)
      UNPROTECTED  0x0010 image hash (32 B), then the scheme's records --
                   classic: 0x00A0 + 0x00A1, two Ed25519 signatures (64 B each)
                   founder: 0x00A4..0x00A8, the founder material

    The sigmask has to be PROTECTED (inside the image hash) or the acceptance
    predicates would be reading an attacker-controlled key selection. Getting the
    record set exactly right matters because the per-scheme shape whitelist demands
    EXACTLY these and nothing else.

    Both shapes are needed. The leaf is the same for both (H(0x00 || image hash)),
    but the unprotected area differs, and it is the area that the per-scheme shape
    whitelist and acceptance predicate act on.
    """
    hdr_size, imgsz = 32, len(body)
    # sigmask: 0x03 (keys 0 and 1) for classic, matching what build_sign_flash.sh
    # passes; a 0x00 placeholder for founder, which the signer patches later.
    prot_tlvs = struct.pack("<HH", TLV_SIGMASK, 1) + bytes([0x00 if founder else 0x03])
    prot_tlvs += struct.pack("<HH", TLV_MODEL_ID, 4) + model_tag
    prot_area = struct.pack("<HH", TLV_PROT_INFO_MAGIC, 4 + len(prot_tlvs)) + prot_tlvs
    header = _MCUBOOT_HDR.pack(
        IMAGE_MAGIC, 0, hdr_size, len(prot_area), imgsz, 0, 9, 9, 9, 9, 0
    )
    # The image-hash TLV must carry the REAL hash: the leaf is that value, so a
    # stand-in here would make the fixture self-inconsistent in exactly the way
    # MCUboot rejects. Computed over header+body+protected area, which is fully
    # determined at this point.
    covered = header + b"\x00" * (hdr_size - _MCUBOOT_HDR.size) + body + prot_area
    unprot_tlvs = struct.pack("<HH", MCUBOOT_TLV_SHA256, 32) + _sha256(covered)
    if not founder:
        # Two signatures: the classic scheme is 2-of-3, so both records always
        # exist. Values are placeholders -- only the SHAPE is exercised here; the
        # real Ed25519 verification is the signature harness's job.
        unprot_tlvs += (
            struct.pack("<HH", LEGACY_TLV_SIG_0, LEGACY_SIG_LEN)
            + b"\xab" * LEGACY_SIG_LEN
        )
        unprot_tlvs += (
            struct.pack("<HH", LEGACY_TLV_SIG_1, LEGACY_SIG_LEN)
            + b"\xcd" * LEGACY_SIG_LEN
        )
    if founder:
        # Founder material: the REAL record set at REAL sizes (so the shape check
        # is exercised for what it will actually see), and LAST in the area with no
        # slack -- slack would be smuggling room for a rogue TLV.
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
    """MCUboot's own image hash: SHA-256 over hdr + payload + protected TLVs.

    Exactly the range bootutil_img_hash covers, and the value that belongs in TLV
    0x10 (verified against the committed image in tests).
    """
    return _sha256(image[: mcuboot_prot_end(image)])


def set_protected_sigmask(image: bytes, sigmask: int) -> bytes:
    """Write the founder `sigmask` into the image's PROTECTED sigmask TLV, keeping
    MCUboot's image-hash TLV consistent.

    The signer owns this field, exactly as it owns the STM boot header's sigmask: it
    sets the value, THEN the leaf is computed, THEN it signs. Being protected, the
    mask is inside MCUboot's image hash AND inside the founder leaf, so it is
    genuinely committed -- the founder signature attests to WHICH keys signed,
    rather than the verifier inferring it. And because the signer (not the nRF
    build) writes it, rotating founder keys needs only a re-sign, not an nRF rebuild.

    Patching a protected TLV invalidates MCUboot's image hash, so TLV 0x10 is
    recomputed here; MCUboot would otherwise reject the image on its hash check.
    Must be called BEFORE the leaf/tree is computed.
    """
    if not 0 <= sigmask <= 0xFF:
        raise ValueError(f"sigmask {sigmask} out of range")

    out = bytearray(image)
    magic, _load, hdr, prot, imgsz, *_rest = _MCUBOOT_HDR.unpack_from(out)
    if magic != IMAGE_MAGIC:
        raise ValueError("not an MCUboot image (bad magic)")
    if prot == 0:
        raise ValueError("image has no protected TLV area to hold the sigmask")

    # Locate the sigmask record inside the PROTECTED area only (a same-typed record
    # in the unprotected area would not be committed, so it must not be used).
    prot_off = hdr + imgsz
    p, end = prot_off + 4, prot_off + prot
    while p + 4 <= end:
        t, ln = struct.unpack_from("<HH", out, p)
        if t == TLV_SIGMASK:
            if ln != 1:
                raise ValueError(f"protected sigmask TLV has length {ln}, expected 1")
            out[p + 4] = sigmask
            break
        p += 4 + ln
    else:
        raise ValueError(
            f"no protected sigmask TLV (0x{TLV_SIGMASK:04x}); the nRF image must be "
            "built with a placeholder (imgtool --custom-tlv) for the signer to fill"
        )

    # Re-stamp MCUboot's image hash over the (now modified) protected region.
    digest = mcuboot_image_hash(bytes(out))
    hp, hend = prot_off + prot + 4, len(out)
    info_magic, info_len = struct.unpack_from("<HH", out, prot_off + prot)
    if info_magic != TLV_INFO_MAGIC:
        raise ValueError("image has no unprotected TLV area (no image-hash TLV)")
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


def add_pq_placeholders(image: bytes) -> bytes:
    """Append ZEROED founder records to the image's unprotected TLV area, making it
    PQ-NATIVE (its own MCUboot will verify the founder tree; see
    CONFIG_BOOT_PQ_SECURE_BOOT).

    Placeholders first, values later, because the material is self-referential: the
    founder signature covers modelRoot, which comes from the leaf, which covers
    `it_tlv_tot` -- so the records' SIZES must already be in the image when the leaf
    is computed, while their CONTENTS cannot be known until after signing. Hence
    add_pq_placeholders() -> build tree -> sign -> fill_pq_material(),
    the latter writing only bytes past the leaf cut.

    The image's existing protected sigmask TLV (0x00A2) doubles as the founder
    sigmask: it must already name the founder keys that will sign (it is protected,
    so it cannot be changed here without invalidating the image's own hash).
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
    # Anything after the TLV area (padding) is dropped: it is outside both the leaf
    # and MCUboot's view, and the bundle re-pads for flash alignment anyway.
    return bytes(out)


def fill_pq_material(
    image: bytes, slh_sigs: list[bytes], ec_sigs: list[bytes], co_path: list[bytes]
) -> bytes:
    """Write the founder signatures + co-path into the placeholders.

    Must NOT change the leaf -- everything written lies in the unprotected TLV
    area, outside MCUboot's image hash. Asserted, because the founder signs
    modelRoot and so cannot appear inside its own preimage.
    """
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
    assert nrf_leaf(filled) == nrf_leaf(
        image
    ), "filling founder material moved the leaf"
    return filled


# --- classic (legacy) signing, for test fixtures only ---------------------------


def legacy_key_slots(sigmask: int, key_count: int) -> tuple[int, int] | None:
    """Which pool keys the sigmask names, or None if it is not a legal selection.

    Mirror of nrf_image_legacy_sig_slots() in io/nrf/nrf_image.c and of
    MCUboot's own expression. NOT the founder scheme's "i-th lowest set bit": this
    is a bespoke 2-of-3 map, and getting it wrong makes the STM predict the wrong
    keys. Cross-checked over all 256 masks by tests/fw_merkle.
    """
    if bin(sigmask).count("1") != 2 or (sigmask & ~0x07) != 0:
        return None
    i0 = 0 if (sigmask & 0x01) else 1
    i1 = 2 if (sigmask & 0x04) else 1
    if i0 == i1 or i0 >= key_count or i1 >= key_count:
        return None
    return (i0, i1)


def legacy_sign(image: bytes, secret_keys: list[bytes], sigmask: int) -> bytes:
    """Sign a CLASSIC image the way the nRF's MCUboot will verify it.

    The two Ed25519 records cover the MCUboot IMAGE HASH -- not the image bytes --
    and the PROTECTED sigmask names which pool keys signed, by slot. Both records
    must already exist as placeholders (see _fake_mcuboot_image): writing them does
    not move the image hash, since they live in the unprotected area.

    For FIXTURES only. Production classic images are signed by
    nordic/trezor/scripts/insert_signatures.py from an offline key.
    """
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


def _find_unprot_tlv_offset(image: bytes, want: int) -> int:
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


def smuggle_rogue_tlv(image: bytes) -> bytes:
    """Adversarial variant: a ROGUE TLV hidden in the unprotected TLV area.

    Splits a record into a shorter one plus a rogue record of the same TOTAL size,
    so every byte below prot_end -- everything the image hash, and hence the leaf,
    covers -- is unchanged. Therefore the leaf, modelRoot and the signature all
    still verify, and so would a full signature re-verify -- yet the co-processor,
    which whitelists unprotected TLV types, would REJECT the image. Only a shape
    check catches this.

    Works for BOTH schemes, since both now have a shape whitelist: it splits the
    first founder record for a PQ-native image, or the first Ed25519 signature
    record for a classic one.
    """
    cut = pq_material_offset(image)
    if cut is None:
        # Classic image: no founder material, so target its first signature record.
        # It must lie ABOVE prot_end -- a rogue inside the hashed range would change
        # the leaf, which is a different (and already covered) test.
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
    my_model = bytes(bl.header.hw_model.value)

    other_model_leaf = _sha256(b"stand-in-other-model-boot-header")
    other_image = _fake_mcuboot_image(b"T3T2", b"other-nrf-body" * 500)

    pq_image = _fake_mcuboot_image(my_model, b"pq-native-nrf-body" * 400, founder=True)

    model_val = model_leaf_value(bl)  # sizes the model path, then reads the stable leaf
    # Slot values are nrf_leaf_value(image), never the raw image (see nrf_leaf).
    slots = [
        model_val,
        nrf_leaf_value(image),
        other_model_leaf,
        nrf_leaf_value(other_image),  # [A-STM, A-nRF, B-STM, B-nRF]
        nrf_leaf_value(pq_image),
    ]  # + a PQ-native shape (founder TLVs)
    model_root, proofs = build_model_tree(slots)

    sign_bootloader_in_tree(bl, proofs[0])
    assert bl.merkle_root() == model_root, "boot-header fold != modelRoot"
    bl.verify(dev_keys=True)  # the ONE signature, over modelRoot

    ota = build_nrf_ota(image, proofs[1])
    print(
        f"MODEL_TREE_DEPTH={MODEL_TREE_DEPTH} ({MODEL_TREE_LEAVES} slots); modelRoot {model_root.hex()[:16]}"
    )
    print(
        f"image model_id={mcuboot_model_id(image)!r} version={mcuboot_version(image)}"
        f"  hashed range {mcuboot_prot_end(image)}/{len(image)} B"
        " (leaf = H(0x00 || that hash))"
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
    # CLASSIC image: tamper below prot_end is caught by the fold, because that range
    # is what the image hash -- hence the leaf -- covers.
    ok &= reject(
        "flipped byte in the body", flip(ota, img_off + mcuboot_prot_end(image) // 2)
    )
    # Its own Ed25519 signature TLVs sit in the UNPROTECTED area, outside the hash,
    # so tampering there still folds. Not a gap: the STM predicts the nRF's verdict
    # on those records before pushing (nrf_image_legacy_accept_ok), which is a stronger
    # statement than the fold could make. Shown so the boundary cannot drift.
    try:
        verify_nrf_ota(model_root, flip(ota, len(ota) - 1), my_model)
        print(
            "  (by design) classic unprotected-TLV tamper still folds -- the STM"
            " verifies those signatures itself before pushing"
        )
    except Exception as e:  # noqa: BLE001
        print(f"  !! FAIL: classic unprotected tamper broke the fold: {e}")
        ok = False

    # PQ-NATIVE image: same boundary, same consequence. The founder material signs
    # modelRoot, so it cannot lie inside its own preimage -> tampering there still
    # folds, BY DESIGN. That is precisely why the STM must ALSO verify the founder
    # material before overwriting a working nRF (no dual slot).
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
