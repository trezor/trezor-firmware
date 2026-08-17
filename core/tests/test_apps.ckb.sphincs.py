# flake8: noqa: F403,F405
from common import *  # isort:skip

# The SPHINCS+ C module is built for T3W1 only (core/SConscript.unix).
_CKB = not utils.BITCOIN_ONLY and utils.INTERNAL_MODEL == "T3W1"

if _CKB:
    from trezor.crypto import sphincsplus
    from trezor.wire import DataError

    from apps.ckb.get_sphincs_address import (
        _VALID_VARIANTS,
        _VARIANT_SIG_BYTES,
        _VARIANT_SPX_N,
        _address_from_pubkey,
        _compute_lock_args,
        _split_extended_mnemonic_to_seed,
        _variant_name,
    )

    MNEMONIC_36 = " ".join(
        ["all"] * 12 + ["abandon"] * 11 + ["about"] + ["zoo"] * 11 + ["abstract"]
    )
    MNEMONIC_54 = " ".join(
        ["abandon"] * 17
        + ["agent"]
        + ["all"] * 17
        + ["action"]
        + ["zoo"] * 17
        + ["advice"]
    )
    MNEMONIC_72 = " ".join(
        ["abandon"] * 23
        + ["art"]
        + ["all"] * 23
        + ["answer"]
        + ["zoo"] * 23
        + ["buddy"]
    )

    # Consensus goldens for MNEMONIC_36 / account 0 / variant 49: PUB_SEED pins
    # the HKDF info strings, PK.root pins the vendored keygen. Shared with
    # test_sphincs_message.py::_EXPECTED_PUBLIC_KEY.
    PUBLIC_KEY_49 = unhexlify(
        "039d22a9fd452e14a7185ba56ea7ad8c158a386451dbee00384796e9288e9471"
    )
    LOCK_ARGS_49 = unhexlify(
        "e6d92a948203f8b16a9326431b32ce1acd68c567462124b70f1c6d2a5b88f876"
    )
    ADDRESS_49 = {
        "Mainnet": (
            "ckb1qqcz6dvc97r9a097mwdfxc8yq5cw6v4dhrsskshmhecdsvf07l8d7q0xmy4ffqsrlz"
            "ck4yexgvdn9ns6e45v2e6xyyjtwrcud549hz8cwclwtx07"
        ),
        "Testnet": (
            "ckt1qq28aja4c5f8mxpwuymz6tptksn8sq7696cqd52saz90dj42pfl27qhxmy4ffqsrlz"
            "ck4yexgvdn9ns6e45v2e6xyyjtwrcud549hz8cwc02mr5v"
        ),
    }


@unittest.skipUnless(_CKB, "CKB is T3W1 only")
class TestSphincsMnemonicSplit(unittest.TestCase):
    def test_36_words_yield_3x16_bytes(self):
        seed = _split_extended_mnemonic_to_seed(MNEMONIC_36.encode())
        self.assertEqual(
            hexlify(bytes(seed)),
            b"0660cc198330660cc198330660cc1983"
            b"00000000000000000000000000000000"
            b"ffffffffffffffffffffffffffffff80",
        )

    def test_54_words_yield_3x24_bytes(self):
        seed = _split_extended_mnemonic_to_seed(MNEMONIC_54.encode())
        self.assertEqual(
            hexlify(bytes(seed)),
            b"000000000000000000000000000000000000000000000000"
            b"0660cc198330660cc198330660cc198330660cc198330660"
            b"ffffffffffffffffffffffffffffffffffffffffffffffe0",
        )

    def test_72_words_yield_3x32_bytes(self):
        seed = _split_extended_mnemonic_to_seed(MNEMONIC_72.encode())
        self.assertEqual(
            hexlify(bytes(seed)),
            b"0000000000000000000000000000000000000000000000000000000000000000"
            b"0660cc198330660cc198330660cc198330660cc198330660cc198330660cc198"
            b"fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8",
        )

    def test_rejects_standard_word_counts(self):
        for count in (12, 18, 24, 35, 37):
            with self.assertRaises(DataError):
                _split_extended_mnemonic_to_seed(b" ".join([b"all"] * count))

    def test_rejects_repeated_sub_phrases(self):
        # Equal sub-phrases would put SK_SEED-deriving entropy on chain via the
        # published PUB_SEED.
        chunk = ["all"] * 12
        other = ["abandon"] * 11 + ["about"]
        for degenerate in (
            chunk + other + chunk,
            chunk + chunk + chunk,
            chunk + chunk + other,
            other + chunk + chunk,
        ):
            with self.assertRaises(DataError):
                _split_extended_mnemonic_to_seed(" ".join(degenerate).encode())


@unittest.skipUnless(_CKB, "CKB is T3W1 only")
class TestSphincsKeyDerivation(unittest.TestCase):
    def test_public_key_golden(self):
        seed = _split_extended_mnemonic_to_seed(MNEMONIC_36.encode())
        public_key = sphincsplus.derive_public_key(seed, 0, 49)
        self.assertEqual(bytes(public_key), PUBLIC_KEY_49)

    def test_lock_args_and_address_golden(self):
        self.assertEqual(_compute_lock_args(PUBLIC_KEY_49, 49), LOCK_ARGS_49)
        for network, expected in ADDRESS_49.items():
            self.assertEqual(_address_from_pubkey(PUBLIC_KEY_49, 49, network), expected)

    def test_account_index_keys_a_different_wallet(self):
        # Pinned, not just "different": a derivation ignoring the index would
        # satisfy assertNotEqual.
        seed = _split_extended_mnemonic_to_seed(MNEMONIC_36.encode())
        self.assertEqual(
            hexlify(sphincsplus.derive_public_key(seed, 1, 49)),
            b"6cc1e06c9178b1ba7f353e34e740990210a1d42e2f3ea041b75408a37663034b",
        )

    def test_sign_verify_roundtrip(self):
        seed = _split_extended_mnemonic_to_seed(MNEMONIC_36.encode())
        # FIPS 205 pure prefix, then 32 filler bytes standing in for a digest.
        message = b"\x00\x00" + b"m" * 32

        public_key, signature = sphincsplus.derive_and_sign(seed, 0, 49, message)

        self.assertEqual(bytes(public_key), PUBLIC_KEY_49)
        self.assertEqual(len(signature), _VARIANT_SIG_BYTES[49])
        # No positive verify(): derive_and_sign sign-then-verifies in C, so it
        # could not have returned otherwise; only the negative adds coverage.
        self.assertFalse(sphincsplus.verify(public_key, signature, message + b"!", 49))


@unittest.skipUnless(_CKB, "CKB is T3W1 only")
class TestSphincsVariantTables(unittest.TestCase):
    # variant id -> (n, signature bytes), spelled out from FIPS 205: deriving n
    # from _VARIANT_SPX_N would let a mis-assignment in BOTH tables pass.
    EXPECTED = {
        48: (16, 17088),  # SHA2_128F
        49: (16, 7856),  # SHA2_128S
        50: (24, 35664),  # SHA2_192F
        51: (24, 16224),  # SHA2_192S
        52: (32, 49856),  # SHA2_256F
        53: (32, 29792),  # SHA2_256S
        54: (16, 17088),  # SHAKE_128F
        55: (16, 7856),  # SHAKE_128S
        56: (24, 35664),  # SHAKE_192F
        57: (24, 16224),  # SHAKE_192S
        58: (32, 49856),  # SHAKE_256F
        59: (32, 29792),  # SHAKE_256S
    }

    def test_valid_variants_are_the_full_range(self):
        self.assertEqual(sorted(_VALID_VARIANTS), list(range(48, 60)))
        self.assertEqual(sorted(_VARIANT_SPX_N), sorted(_VALID_VARIANTS))
        self.assertEqual(sorted(_VARIANT_SIG_BYTES), sorted(_VALID_VARIANTS))

    def test_tables_match_fips205(self):
        for variant, (n, sig_bytes) in self.EXPECTED.items():
            self.assertEqual(_VARIANT_SPX_N[variant], n)
            self.assertEqual(_VARIANT_SIG_BYTES[variant], sig_bytes)

    def test_variant_names(self):
        self.assertEqual(_variant_name(49), "SHA2_128S")
        self.assertEqual(_variant_name(48), "SHA2_128F")
        self.assertEqual(_variant_name(53), "SHA2_256S")
        self.assertEqual(_variant_name(55), "SHAKE_128S")
        self.assertEqual(_variant_name(58), "SHAKE_256F")


if __name__ == "__main__":
    unittest.main()
