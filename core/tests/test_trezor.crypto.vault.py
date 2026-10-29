# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import (
    SecretOwner,
    _secret_owner_activate,
    bip32,
    bip39,
    revoke_secrets,
    secbytes,
)

from trezor import config
from trezor.crypto.curve import secp256k1

MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
DIGEST = b"\x42" * 32


class TestVault(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        self.owner = SecretOwner()
        _secret_owner_activate(self.owner)
        config.set(1, 2, MNEMONIC.encode())
        config.set(1, 0x0E, b"\x00")

    def tearDown(self):
        revoke_secrets()

    def test_storage_seed_is_opaque_and_matches_bip39(self):
        for passphrase in ("", "TREZOR"):
            seed = bip32.from_storage(passphrase)
            self.assertIsInstance(seed, secbytes)
            with self.assertRaises(TypeError):
                bytes(seed)
            actual = bip32.from_seed(seed, "secp256k1")
            expected = bip32.from_seed(bip39.seed(MNEMONIC, passphrase), "secp256k1")
            actual.derive_path([0x8000002C, 0x80000000, 0x80000000, 0, 0])
            expected.derive_path([0x8000002C, 0x80000000, 0x80000000, 0, 0])
            self.assertEqual(actual.public_key(), expected.public_key())
            self.assertEqual(
                secp256k1.sign(actual.private_key(), DIGEST),
                secp256k1.sign(expected.private_key(), DIGEST),
            )

    def test_passphrase_bounds(self):
        # 50 Unicode characters may occupy the full 200-byte UTF-8 bound.
        seed = bip32.from_storage("\U0001f600" * 50)
        self.assertIsInstance(seed, secbytes)
        for invalid in ("x" * 201, "contains\x00nul"):
            with self.assertRaises(ValueError):
                bip32.from_storage(invalid)
        # Rejections must leave the existing seed usable.
        node = bip32.from_seed(seed, "secp256k1")
        self.assertEqual(len(node.public_key()), 33)

    def test_raw_storage_reads_and_aliases_denied(self):
        config.set(1, 0x25, b"binary mnemonic")
        for key in (2, 0x25):
            self.assertIsNone(config.get(1, key))
            config.set(1, key, b"public alias", True)
            self.assertIsNone(config.get(1, key, True))

    def test_lock_gates_existing_handles_but_preserves_session(self):
        seed = bip32.from_storage()
        node = bip32.from_seed(seed, "secp256k1")
        key = node.private_key()
        signature = secp256k1.sign(key, DIGEST)
        config.lock()
        # Cloning copies a sealed blob and grants nothing: every use of the
        # copy is gated like the original.
        clone = node.clone()
        for action in (
            lambda: bip32.from_storage(),
            lambda: clone.private_key(),
            lambda: clone.derive(1),
            lambda: node.private_key(),
            lambda: node.derive(1),
            lambda: secp256k1.sign(key, DIGEST),
        ):
            with self.assertRaises(ValueError):
                action()
        self.assertTrue(self.owner.valid())
        self.assertTrue(config.unlock("", None))
        self.assertEqual(secp256k1.sign(key, DIGEST), signature)
        config.lock()
        self.owner.destroy()
        self.assertTrue(config.unlock("", None))
        with self.assertRaises(ValueError):
            secp256k1.sign(key, DIGEST)

    def test_raw_config_wipe_revokes_handles(self):
        node = bip32.from_seed(bip32.from_storage(), "secp256k1")
        key = node.private_key()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        self.assertFalse(self.owner.valid())
        with self.assertRaises(ValueError):
            secp256k1.sign(key, DIGEST)

    def test_unsupported_inputs_fail_closed(self):
        config.set(1, 0x0E, b"\x01")
        with self.assertRaises(ValueError):
            bip32.from_storage()
        with self.assertRaises(ValueError):
            bip32.from_seed(b"seed", "unsupported-curve")


if __name__ == "__main__":
    unittest.main()
