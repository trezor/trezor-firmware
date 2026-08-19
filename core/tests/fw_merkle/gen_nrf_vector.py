#!/usr/bin/env python3
"""Emit a C test vector for nrf_crossvalidate.c.

Builds two nRF MCUboot images (this model + another model) as leaves of one
founder model tree, so the C side can check the COMBINED device verify:
  * nrf_image_verify_in_tree (fold leaf+co-path -> modelRoot), and
  * nrf_image_model_id (the model-id TLV pins the image to THIS model -- both
    images fold to modelRoot, only the model id separates them).
Computed by the host nrf_tree module so C is checked against Python.

Usage: gen_nrf_vector.py <out.h>
"""

import struct
import sys

sys.path.insert(0, "core/tools")
from trezor_core_tools import nrf_tree  # noqa: E402

DEVICE_MODEL = b"T3W1"
OTHER_MODEL = b"T3T2"

# A classic-scheme key pool for the fixtures. Fixed seeds, so the vector is
# reproducible; the C side is handed the PUBLIC halves as its MODEL_NRF_LEGACY_KEYS_*
# and so verifies real signatures rather than a stub. Test-only, obviously -- the
# real pool is the nRF's, mirrored in the model header.
LEGACY_SECRET_KEYS = [b"nrf-legacy-test-key-%d" % i + b"\x00" * 10 for i in range(3)]
LEGACY_SIGMASK = 0x03  # keys 0 and 1 -- what build_sign_flash.sh passes


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
    """The six adversarial length mutations, as (C name, image, description).

    Every one of these lives in the UNPROTECTED area or the header -- so none of
    them changes the image hash, hence none changes the leaf, hence the FOLD STILL
    PASSES on all of them. They are unreachable through the fold by construction;
    only the parser's bounds checks stand between them and an over-read. That is
    what made them untestable while the leaf covered it_tlv_tot.
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
    # 4. header lengths chosen so a 32-BIT sum of hdr+img+prot would wrap to a
    #    small (passing) value. The parser sums in 64-bit, so it must reject.
    wrapped = bytearray(image)
    struct.pack_into("<I", wrapped, 12, 0xFFFFFF00)  # ih_img_size
    out.append(
        ("HDR_WRAP", bytes(wrapped), "header lengths that would wrap a 32-bit sum")
    )
    # 5. a 2-byte stub after the valid records: too small to be a record, and
    #    silently stopping instead of failing would let one be appended
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
    assert prot_end  # silence the unused-name lint; kept for readability above
    return out


def main() -> None:
    out = sys.argv[1]
    # Two shapes. The LEAF is the same rule for both (MCUboot's image hash), so
    # what these exercise is everything downstream of it: which acceptance predicate
    # applies, and what the shape check expects in the unprotected area.
    #   NRF_IMAGE  -- CLASSIC    (no founder TLVs, its own Ed25519 records)
    #   PQ_IMAGE   -- PQ-NATIVE  (founder signature + co-path records)
    nrf_image = nrf_tree._fake_mcuboot_image(DEVICE_MODEL, b"nrf-body-this-model" * 40)
    other_image = nrf_tree._fake_mcuboot_image(
        OTHER_MODEL, b"nrf-body-other-model" * 40
    )
    pq_image = nrf_tree._fake_mcuboot_image(
        DEVICE_MODEL, b"nrf-body-pq-native" * 40, founder=True
    )
    # Sign the CLASSIC fixtures for real, so the acceptance predicate is exercised
    # end-to-end. Must happen BEFORE the tree is built: the sigmask is a PROTECTED
    # TLV, so stamping it moves the image hash and hence the leaf.
    nrf_image = nrf_tree.legacy_sign(nrf_image, LEGACY_SECRET_KEYS, LEGACY_SIGMASK)
    other_image = nrf_tree.legacy_sign(other_image, LEGACY_SECRET_KEYS, LEGACY_SIGMASK)
    # Slot values are nrf_leaf_value(image), never the raw image (see nrf_leaf).
    slots = [
        nrf_tree.nrf_leaf_value(nrf_image),
        nrf_tree.nrf_leaf_value(other_image),
        nrf_tree.nrf_leaf_value(pq_image),
        b"stm-leaf-A",
    ]
    model_root, proofs = nrf_tree.build_model_tree(slots)

    # Fill the PQ-native fixture's material for real, now that the tree exists: the
    # signatures are stand-ins (no host SLH-DSA), but the MERKLE PROOF must be the
    # genuine one, because the STM's push gate folds with the copy carried in the
    # IMAGE -- that is the copy the nRF's MCUboot uses. All of it lands past the leaf
    # cut, so the leaf, the slot value and the proofs above stay valid (asserted
    # inside fill_pq_material).
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

    # Full OTA artifacts (proof_count || co_path || image) -- the wire form the
    # host sends. The device never parses this as one buffer: the bootloader
    # streams it and keeps co_path/image_len in its staging descriptor. The
    # harness unpacks it (harness_ota_gate) to reach the same two primitives.
    nrf_ota = nrf_tree.build_nrf_ota(nrf_image, proofs[0])
    other_ota = nrf_tree.build_nrf_ota(other_image, proofs[1])
    pq_ota = nrf_tree.build_nrf_ota(pq_image, proofs[2])

    with open(out, "w") as f:
        f.write("/* generated by gen_nrf_vector.py -- do not edit */\n")
        f.write(
            f"static const unsigned char DEVICE_MODEL_ID[4] = {{{_carr(DEVICE_MODEL)}}};\n"
        )
        _emit_image(f, "NRF_IMAGE", nrf_image)
        _emit_proof(f, "NRF_PROOF", proofs[0])
        _emit_image(f, "OTHER_IMAGE", other_image)
        _emit_proof(f, "OTHER_PROOF", proofs[1])
        f.write(
            f"static const unsigned char NRF_MODEL_ROOT[32] = {{{_carr(model_root)}}};\n"
        )
        _emit_image(f, "NRF_OTA", nrf_ota)
        _emit_image(f, "OTHER_OTA", other_ota)
        _emit_image(f, "PQ_IMAGE", pq_image)
        _emit_proof(f, "PQ_PROOF", proofs[2])
        _emit_image(f, "PQ_OTA", pq_ota)
        # Adversarial: a rogue TLV smuggled into the founder region. The leaf (and
        # so modelRoot and the founder signature) is untouched, so the fold STILL
        # PASSES -- MCUboot would reject it on its unprotected-TLV whitelist. Only a
        # shape check catches it. Assert the premise, or the case proves nothing.
        pq_rogue = nrf_tree.smuggle_rogue_tlv(pq_image)
        assert nrf_tree.nrf_leaf(pq_rogue) == nrf_tree.nrf_leaf(
            pq_image
        ), "rogue variant must keep the leaf intact (else it proves nothing)"
        assert len(pq_rogue) == len(pq_image)
        _emit_image(f, "PQ_IMAGE_ROGUE", pq_rogue)
        _emit_image(f, "PQ_OTA_ROGUE", nrf_tree.build_nrf_ota(pq_rogue, proofs[2]))
        # The SAME attack against a CLASSIC image, which now has a shape whitelist
        # of its own. Here the premise is even sharper: the two Ed25519 signatures
        # cover the image hash, which the rogue record does not change, so the
        # signatures verify AND the fold passes -- yet the nRF rejects on its
        # allow-list, after the STM has already erased its only slot.
        nrf_rogue = nrf_tree.smuggle_rogue_tlv(nrf_image)
        assert nrf_tree.nrf_leaf(nrf_rogue) == nrf_tree.nrf_leaf(
            nrf_image
        ), "classic rogue variant must keep the leaf intact (else it proves nothing)"
        assert len(nrf_rogue) == len(nrf_image)
        _emit_image(f, "NRF_IMAGE_ROGUE", nrf_rogue)

        # Bounds discipline: six adversarial length mutations. The fold passes on
        # every one of them (none touches the hashed range), so the parser's checks
        # are the ONLY defence -- which is exactly what dropping the it_tlv_tot
        # commitment made load-bearing.
        variants = _bounds_variants(pq_image)
        # The premise: these are invisible to the fold. Assert it for every mutation
        # that leaves the header alone (HDR_WRAP deliberately breaks the hash range,
        # which is the point of that one).
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

        # The classic acceptance predicate, end to end. The C side gets the PUBLIC
        # pool and verifies these for real; each negative breaks exactly one thing.
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
        # the two signatures exchanged: each is valid, but for the OTHER slot. Only
        # the slot->key map catches it, which is the part most likely to drift.
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
        # Offsets so the C side can tamper deliberately INSIDE vs OUTSIDE the range
        # the leaf commits, for BOTH shapes. That range is MCUboot's protected
        # region, so the boundary is the same rule for classic and PQ-native alike.
        img_off = nrf_tree._PROOF_COUNT.size + len(proofs[0]) * nrf_tree._NODE
        classic_prot_end = nrf_tree.mcuboot_prot_end(nrf_image)
        pq_prot_end = nrf_tree.mcuboot_prot_end(pq_image)
        # Both shapes must have something OUTSIDE the hashed range, or the "tamper
        # outside still folds" cases would silently degenerate into no-ops.
        assert classic_prot_end < len(
            nrf_image
        ), "classic image has no unprotected area"
        assert pq_prot_end < len(pq_image), "PQ-native image has no unprotected area"
        assert not nrf_tree.has_pq_material(
            nrf_image
        ), "classic fixture carries founder TLVs"
        assert nrf_tree.has_pq_material(
            pq_image
        ), "PQ-native fixture carries no founder TLVs"
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
