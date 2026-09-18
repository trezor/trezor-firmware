#!/usr/bin/env python3
"""Emit the C test vector for nrf_crossvalidate.c.

Two nRF MCUboot images (this model + another model) as leaves of one founder
model tree, plus adversarial variants, all computed by the host nrf_tree module.
Usage: gen_nrf_vector.py <out.h>
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from trezor_core_tools import nrf_tree  # noqa: E402

DEVICE_MODEL = b"T3W1"
OTHER_MODEL = b"T3T2"

# Test-only classic key pool, fixed seeds; the C side gets the public halves.
LEGACY_SECRET_KEYS = [b"nrf-legacy-test-key-%d" % i + b"\x00" * 10 for i in range(3)]
LEGACY_SIGMASK = 0x03  # keys 0 and 1, as build_sign_flash.sh passes


def _carr(b: bytes) -> str:
    return ", ".join(str(x) for x in b)


def _emit_image(f, name: str, image: bytes) -> None:
    f.write(f"static const unsigned char {name}[] = {{{_carr(image)}}};\n")
    f.write(f"static const unsigned int {name}_LEN = {len(image)};\n")


def _emit_proof(f, name: str, proof: list) -> None:
    f.write(f"static const unsigned int {name}_COUNT = {len(proof)};\n")
    f.write(f"static const unsigned char {name}[][32] = {{\n")
    for node in proof:
        f.write(f"  {{{_carr(node)}}},\n")
    f.write("};\n")


def _poke16(image: bytes, off: int, value: int) -> bytes:
    b = bytearray(image)
    struct.pack_into("<H", b, off, value)
    return bytes(b)


def _tlv_tot_off(image: bytes) -> int:
    """Offset of it_tlv_tot: the unprotected TLV-info header's length field."""
    return nrf_tree.mcuboot_prot_end(image) + 2


def _bounds_variants(image: bytes) -> list[tuple[str, bytes, str]]:
    """Six adversarial length mutations, as (C name, image, description).

    All live outside the hashed range, so the fold still passes on every one;
    only the parser's bounds checks stand between them and an over-read.
    """
    prot_end = nrf_tree.mcuboot_prot_end(image)
    tot_off = _tlv_tot_off(image)
    tot = struct.unpack_from("<H", image, tot_off)[0]
    # offset + declared length of the LAST unprotected record (the Merkle proof)
    last = nrf_tree._find_unprot_tlv_offset(image, nrf_tree.PQ_TLV_MERKLE_PROOF)
    last_len = struct.unpack_from("<H", image, last + 2)[0]

    out = []
    # 1. declared extent runs past the end of the image entirely
    out.append(
        (
            "TLVTOT_BIG",
            _poke16(image, tot_off, 0xFFFF),
            "it_tlv_tot past the end of the image",
        )
    )
    # 2. declared extent inflated to swallow trailing bytes as if they were records
    out.append(
        (
            "TLVTOT_INNER",
            _poke16(image + b"\x00" * 8, tot_off, tot + 8),
            "it_tlv_tot inflated over trailing bytes",
        )
    )
    # 3. a record whose declared length overruns tlv_end
    out.append(
        (
            "RECLEN_OVER",
            _poke16(image, last + 2, last_len + 16),
            "record length overruns tlv_end",
        )
    )
    # 4. header lengths whose 32-bit hdr+img+prot sum would wrap; the parser
    #    sums in 64-bit, so it must reject
    wrapped = bytearray(image)
    struct.pack_into("<I", wrapped, 12, 0xFFFFFF00)  # ih_img_size
    out.append(
        ("HDR_WRAP", bytes(wrapped), "header lengths that would wrap a 32-bit sum")
    )
    # 5. a 2-byte trailing stub: too small to be a record, must fail not stop
    out.append(
        (
            "STUB",
            _poke16(image + b"\x5a\x5a", tot_off, tot + 2),
            "2-byte trailing stub after the records",
        )
    )
    # 6. declared extent smaller than the records it should contain
    out.append(
        (
            "TLVTOT_SMALL",
            _poke16(image, tot_off, tot - 16),
            "it_tlv_tot truncated below its records",
        )
    )
    assert prot_end  # silence the unused-name lint
    return out


def main() -> None:
    out = sys.argv[1]
    # Two shapes with the same leaf rule (MCUboot's image hash):
    #   NRF_IMAGE  -- classic   (no founder TLVs, its own Ed25519 records)
    #   PQ_IMAGE   -- PQ-native (founder signature + co-path records)
    nrf_image = nrf_tree._fake_mcuboot_image(DEVICE_MODEL, b"nrf-body-this-model" * 40)
    other_image = nrf_tree._fake_mcuboot_image(
        OTHER_MODEL, b"nrf-body-other-model" * 40
    )
    pq_image = nrf_tree._fake_mcuboot_image(
        DEVICE_MODEL, b"nrf-body-pq-native" * 40, founder=True
    )
    # Sign the classic fixtures before building the tree: the sigmask is a
    # protected TLV, so stamping it moves the leaf.
    nrf_image = nrf_tree.legacy_sign(nrf_image, LEGACY_SECRET_KEYS, LEGACY_SIGMASK)
    other_image = nrf_tree.legacy_sign(other_image, LEGACY_SECRET_KEYS, LEGACY_SIGMASK)
    # Slot values are nrf_leaf_value(image), never the raw image. The other-model
    # image is slotted under THIS device's model so the fold passes and only the
    # model-id TLV separates it (the misissuance case).
    slots = [
        nrf_tree.nrf_leaf_value(nrf_image),
        nrf_tree.coproc_slot_value(
            DEVICE_MODEL,
            nrf_tree.COPROC_KIND_NRF,
            0,
            nrf_tree.mcuboot_image_hash(other_image),
        ),
        nrf_tree.nrf_leaf_value(pq_image),
        b"stm-leaf-A",
    ]
    model_root, proofs = nrf_tree.build_model_tree(slots)

    # Roots over the same slots except for the role fields; neither may fold for
    # a verifier that builds kind/index from its own build configuration.
    wrong_index_root, _ = nrf_tree.build_model_tree(
        [nrf_tree.nrf_leaf_value(nrf_image, index=1)] + slots[1:]
    )
    wrong_kind_root, _ = nrf_tree.build_model_tree(
        [
            nrf_tree.coproc_slot_value(
                DEVICE_MODEL,
                nrf_tree.COPROC_KIND_NRF + 1,
                0,
                nrf_tree.mcuboot_image_hash(nrf_image),
            )
        ]
        + slots[1:]
    )

    # Stand-in signatures (no host SLH-DSA) but the genuine Merkle proof: the
    # STM's push gate folds with the copy carried in the image. All of it lies
    # outside the leaf, so the slots and proofs above stay valid.
    pq_image = nrf_tree.fill_pq_material(
        pq_image,
        [
            bytes([0xA4]) * nrf_tree.PQ_SLH_SIG_LEN,
            bytes([0xA5]) * nrf_tree.PQ_SLH_SIG_LEN,
        ],
        [
            bytes([0xA6]) * nrf_tree.PQ_EC_SIG_LEN,
            bytes([0xA7]) * nrf_tree.PQ_EC_SIG_LEN,
        ],
        proofs[2],
    )

    # Wire-form OTA artifacts (proof_count || co_path || image); the harness
    # unpacks them itself (harness_ota_gate), the bootloader never does.
    nrf_ota = nrf_tree.build_nrf_ota(nrf_image, proofs[0])
    other_ota = nrf_tree.build_nrf_ota(other_image, proofs[1])
    pq_ota = nrf_tree.build_nrf_ota(pq_image, proofs[2])

    with open(out, "w") as f:
        f.write("/* generated by gen_nrf_vector.py -- do not edit */\n")
        f.write(
            f"static const unsigned char DEVICE_MODEL_ID[4] = {{{_carr(DEVICE_MODEL)}}};\n"
            f"static const unsigned char OTHER_MODEL_ID[4] = {{{_carr(OTHER_MODEL)}}};\n"
        )
        _emit_image(f, "NRF_IMAGE", nrf_image)
        _emit_proof(f, "NRF_PROOF", proofs[0])
        _emit_image(f, "OTHER_IMAGE", other_image)
        _emit_proof(f, "OTHER_PROOF", proofs[1])
        f.write(
            f"static const unsigned char NRF_MODEL_ROOT[32] = {{{_carr(model_root)}}};\n"
        )
        f.write(
            "/* roots over slots differing ONLY in the role fields -- a verifier\n"
            "   that builds kind/index from its own config must fold to NEITHER. */\n"
            f"static const unsigned char NRF_WRONG_INDEX_ROOT[32] = {{{_carr(wrong_index_root)}}};\n"
            f"static const unsigned char NRF_WRONG_KIND_ROOT[32] = {{{_carr(wrong_kind_root)}}};\n"
        )
        _emit_image(f, "NRF_OTA", nrf_ota)
        _emit_image(f, "OTHER_OTA", other_ota)
        _emit_image(f, "PQ_IMAGE", pq_image)
        _emit_proof(f, "PQ_PROOF", proofs[2])
        _emit_image(f, "PQ_OTA", pq_ota)
        # Rogue TLV in the founder region: the leaf is intact, so the fold still
        # passes and only the shape check catches it. Assert the premise.
        pq_rogue = nrf_tree.smuggle_rogue_tlv(pq_image)
        assert nrf_tree.nrf_leaf(pq_rogue) == nrf_tree.nrf_leaf(pq_image), (
            "rogue variant must keep the leaf intact (else it proves nothing)"
        )
        assert len(pq_rogue) == len(pq_image)
        _emit_image(f, "PQ_IMAGE_ROGUE", pq_rogue)
        _emit_image(f, "PQ_OTA_ROGUE", nrf_tree.build_nrf_ota(pq_rogue, proofs[2]))
        # Same attack on a classic image: its signatures verify and the fold
        # passes, only the classic shape whitelist sees it.
        nrf_rogue = nrf_tree.smuggle_rogue_tlv(nrf_image)
        assert nrf_tree.nrf_leaf(nrf_rogue) == nrf_tree.nrf_leaf(nrf_image), (
            "classic rogue variant must keep the leaf intact (else it proves nothing)"
        )
        assert len(nrf_rogue) == len(nrf_image)
        _emit_image(f, "NRF_IMAGE_ROGUE", nrf_rogue)
        # Unprotected 0x10 record not matching the computed hash: only
        # comparing its value catches it; unchecked it bricks (MCUboot rejects
        # after the STM erased the slot). Both schemes.
        pq_badhash = nrf_tree.corrupt_hash_tlv(pq_image)
        assert nrf_tree.nrf_leaf(pq_badhash) == nrf_tree.nrf_leaf(pq_image), (
            "bad-hash variant must keep the leaf intact (else it proves nothing)"
        )
        assert len(pq_badhash) == len(pq_image)
        _emit_image(f, "PQ_IMAGE_BADHASH", pq_badhash)
        nrf_badhash = nrf_tree.corrupt_hash_tlv(nrf_image)
        assert nrf_tree.nrf_leaf(nrf_badhash) == nrf_tree.nrf_leaf(nrf_image), (
            "classic bad-hash variant must keep the leaf intact"
        )
        assert len(nrf_badhash) == len(nrf_image)
        _emit_image(f, "NRF_IMAGE_BADHASH", nrf_badhash)

        # Bounds discipline: the fold passes on all six mutations, so the
        # parser's checks are the only defence.
        variants = _bounds_variants(pq_image)
        # Assert the premise for every mutation that leaves the header alone
        # (HDR_WRAP deliberately breaks the hash range).
        for name, img, _d in variants:
            if name == "HDR_WRAP":
                continue
            assert nrf_tree.nrf_leaf(img) == nrf_tree.nrf_leaf(pq_image), (
                f"{name} moved the leaf -- it would be caught by the fold, so it "
                "would not be testing the bounds checks"
            )
        f.write(f"static const unsigned int PQ_BOUNDS_COUNT = {len(variants)};\n")
        for name, img, _desc in variants:
            _emit_image(f, f"PQ_IMAGE_{name}", img)
        f.write(
            "static const struct { const unsigned char *img; unsigned int len;"
            " const char *what; } PQ_BOUNDS[] = {\n"
        )
        for name, _img, desc in variants:
            f.write(f'  {{PQ_IMAGE_{name}, PQ_IMAGE_{name}_LEN, "{desc}"}},\n')
        f.write("};\n")

        # Classic acceptance predicate, end to end: the C side gets the public
        # pool; each negative breaks exactly one thing.
        from trezorlib import _ed25519

        for i, sk in enumerate(LEGACY_SECRET_KEYS):
            pk = _ed25519.publickey_unsafe(sk)
            f.write(
                f"static const unsigned char NRF_LEGACY_KEY_{i}[32] = "
                f"{{{_carr(pk)}}};\n"
            )

        def _flip_sig(image: bytes, tlv: int) -> bytes:
            off = nrf_tree._find_unprot_tlv_offset(image, tlv) + 4
            b = bytearray(image)
            b[off] ^= 0xFF
            return bytes(b)

        # a bad signature in either slot
        _emit_image(
            f, "NRF_IMAGE_BADSIG0", _flip_sig(nrf_image, nrf_tree.LEGACY_TLV_SIG_0)
        )
        _emit_image(
            f, "NRF_IMAGE_BADSIG1", _flip_sig(nrf_image, nrf_tree.LEGACY_TLV_SIG_1)
        )
        # the two signatures exchanged: each valid, but for the other slot
        o0 = nrf_tree._find_unprot_tlv_offset(nrf_image, nrf_tree.LEGACY_TLV_SIG_0) + 4
        o1 = nrf_tree._find_unprot_tlv_offset(nrf_image, nrf_tree.LEGACY_TLV_SIG_1) + 4
        n = nrf_tree.LEGACY_SIG_LEN
        swapped = bytearray(nrf_image)
        swapped[o0 : o0 + n] = nrf_image[o1 : o1 + n]
        swapped[o1 : o1 + n] = nrf_image[o0 : o0 + n]
        _emit_image(f, "NRF_IMAGE_SWAPPED", bytes(swapped))
        # sigmask naming keys 0,2 while keys 0,1 actually signed
        _emit_image(
            f, "NRF_IMAGE_WRONGMASK", nrf_tree.set_protected_sigmask(nrf_image, 0x05)
        )
        # an illegal sigmask: three bits set, so not a 2-of-3 selection at all
        _emit_image(
            f, "NRF_IMAGE_ILLEGALMASK", nrf_tree.set_protected_sigmask(nrf_image, 0x07)
        )
        # a sigmask naming a key outside the pool
        _emit_image(
            f, "NRF_IMAGE_OUTOFPOOL", nrf_tree.set_protected_sigmask(nrf_image, 0x09)
        )
        # Offsets so the C side can tamper inside vs outside the hashed range
        # (MCUboot's protected region) for both shapes.
        img_off = nrf_tree._PROOF_COUNT.size + len(proofs[0]) * nrf_tree._NODE
        classic_prot_end = nrf_tree.mcuboot_prot_end(nrf_image)
        pq_prot_end = nrf_tree.mcuboot_prot_end(pq_image)
        # Both shapes need an unprotected area, or the "tamper outside still
        # folds" cases degenerate into no-ops.
        assert classic_prot_end < len(nrf_image), (
            "classic image has no unprotected area"
        )
        assert pq_prot_end < len(pq_image), "PQ-native image has no unprotected area"
        assert not nrf_tree.has_pq_material(nrf_image), (
            "classic fixture carries founder TLVs"
        )
        assert nrf_tree.has_pq_material(pq_image), (
            "PQ-native fixture carries no founder TLVs"
        )
        f.write(f"static const unsigned int NRF_OTA_IMAGE_OFF = {img_off};\n")
        f.write(f"static const unsigned int NRF_IMAGE_PROT_END = {classic_prot_end};\n")
        f.write(f"static const unsigned int PQ_IMAGE_PROT_END = {pq_prot_end};\n")

    # sanity: host verify agrees before we hand it to C
    info = nrf_tree.verify_nrf_ota(model_root, nrf_ota, DEVICE_MODEL)
    print(
        f"wrote {out}: modelRoot {model_root.hex()[:16]}, host verify {info['model_id']!r} OK"
    )


if __name__ == "__main__":
    main()
