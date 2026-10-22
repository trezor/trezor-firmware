# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import SecretOwner, _secret_owner_activate, revoke_secrets, secbytes

from trezor import config
from trezor.crypto import bip32
from trezor.crypto.curve import ed25519


class TestEd25519Vault(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        self.owner = SecretOwner()
        _secret_owner_activate(self.owner)

    def tearDown(self):
        revoke_secrets()

    def test_known_vector(self):
        # Same independent Tor vector as test_trezor.crypto.curve.ed25519.py.
        key = secbytes(
            bytes.fromhex(
                "26c76712d89d906e6672dafa614c42e5cb1caac8c6568e4d2493087db51f0d36"
            )
        )
        public = bytes.fromhex(
            "c2247870536a192d142d056abefca68d6193158e7c1a59c1654c954eccaff894"
        )
        signature = bytes.fromhex(
            "d23188eac3773a316d46006fa59c095060be8b1a23582a0dd99002a82a0662bd246d8449e172e04c5f46ac0d1404cebe4aabd8a75a1457aa06cae41f3334f104"
        )
        self.assertEqual(ed25519.publickey(key), public)
        self.assertEqual(ed25519.sign(key, public), signature)
        self.assertTrue(ed25519.verify(public, signature, public))

    def test_message_bounds_and_keccak(self):
        self.assertEqual(ed25519.MAX_MESSAGE_SIZE, 2048)
        raw_key = b"\x17" * 32
        key = secbytes(raw_key)
        for length in (1, 256, 257, 1232, 1536, 2048):
            message = b"\x42" * length
            signature = ed25519.sign(key, message)
            self.assertEqual(signature, ed25519.sign(raw_key, message))
            self.assertTrue(ed25519.verify(ed25519.publickey(key), signature, message))
            self.assertEqual(
                ed25519.sign(key, message, "keccak"),
                ed25519.sign(raw_key, message, "keccak"),
            )
        for message in (b"", b"x" * 2049):
            with self.assertRaises(ValueError):
                ed25519.sign(key, message)
        for hasher in ("", "sha512", "keccak!", b"k"):
            with self.assertRaises(ValueError):
                ed25519.sign(key, b"message", hasher)
        self.assertTrue(ed25519.sign(key, b"message"))

    def test_private_snapshot_and_curve(self):
        node = bip32.from_seed(b"\x42" * 16, "ed25519")
        node.derive_path([0x80002726, 0x80000001])
        key = node.private_key()
        public = ed25519.publickey(key)
        self.assertIsInstance(key, secbytes)
        self.assertEqual(node.public_key()[1:], public)
        with self.assertRaises(ValueError):
            node.derive(1)
        self.assertEqual(node.public_key()[1:], public)
        clone = node.clone()
        clone.derive(0x80000002)
        self.assertNotEqual(clone.public_key()[1:], public)
        node.__del__()
        clone.__del__()
        self.assertTrue(
            ed25519.verify(public, ed25519.sign(key, b"message"), b"message")
        )
        for action in (lambda: bytes(key), lambda: memoryview(key), lambda: key[0]):
            with self.assertRaises(TypeError):
                action()
        key.destroy()
        with self.assertRaises(ValueError):
            ed25519.publickey(key)

    def test_imported_private_zero_and_public_only(self):
        raw = b"\x00" * 32
        public = b"\x00" + ed25519.publickey(raw)
        node = bip32.HDNode(
            depth=0,
            fingerprint=0,
            child_num=0,
            chain_code=b"x" * 32,
            private_key=raw,
            public_key=public,
            curve_name="ed25519",
        )
        self.assertEqual(node.public_key(), public)
        self.assertEqual(
            ed25519.sign(node.private_key(), b"message"), ed25519.sign(raw, b"message")
        )
        with self.assertRaises(ValueError):
            bip32.HDNode(
                depth=0,
                fingerprint=0,
                child_num=0,
                chain_code=b"x" * 32,
                public_key=public,
                curve_name="ed25519",
            )

    def test_invalid_keys_lock_and_revocation(self):
        bad_key = secbytes(b"x" * 31)
        with self.assertRaises(ValueError):
            ed25519.sign(bad_key, b"message")
        with self.assertRaises(ValueError):
            ed25519.publickey(bad_key)
        key = bip32.from_seed(b"\x42" * 16, "ed25519").private_key()
        signature = ed25519.sign(key, b"message")
        config.lock()
        for action in (
            lambda: ed25519.sign(key, b"message"),
            lambda: ed25519.publickey(key),
        ):
            with self.assertRaises(ValueError):
                action()
        self.assertTrue(config.unlock("", None))
        self.assertEqual(ed25519.sign(key, b"message"), signature)
        self.owner.destroy()
        for action in (
            lambda: ed25519.sign(key, b"message"),
            lambda: ed25519.publickey(key),
        ):
            with self.assertRaises(ValueError):
                action()


if __name__ == "__main__":
    unittest.main()
