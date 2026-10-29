# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import SecretOwner, _secret_owner_activate, revoke_secrets, secbytes

from trezor import config
from trezor.crypto import bip32, hmac
from trezor.crypto.curve import nist256p1


class TestProtectedFidoKeys(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        self.owner = SecretOwner()
        _secret_owner_activate(self.owner)

    def tearDown(self):
        revoke_secrets()

    def test_p256_snapshot_and_sign(self):
        node = bip32.from_seed(b"\x42" * 16, "nist256p1")
        node.derive_path([0x80553246, 0x80000001])
        key = node.private_key()
        self.assertIsInstance(key, secbytes)
        public = nist256p1.publickey(key, False)
        digest = b"\x5a" * 32
        signature = nist256p1.sign(key, digest, False)
        self.assertTrue(nist256p1.verify(public, signature, digest))
        self.assertEqual(nist256p1.publickey(key), node.public_key())
        node.derive(0x80000002)
        node.__del__()
        self.assertEqual(nist256p1.sign(key, digest, False), signature)
        for action in (lambda: bytes(key), lambda: memoryview(key), lambda: key[0]):
            with self.assertRaises(TypeError):
                action()
        key.destroy()
        with self.assertRaises(ValueError):
            nist256p1.sign(key, digest)

    def test_public_mac_and_bounds(self):
        plaintext = b"\x17" * 32
        key = secbytes(plaintext)
        for algorithm in (hmac.SHA256, hmac.SHA512):
            for message in (b"", b"x" * 64, b"z" * 256):
                self.assertEqual(
                    hmac.tag(algorithm, key, message),
                    hmac(algorithm, plaintext, message).digest(),
                )
        with self.assertRaises(ValueError):
            hmac.tag(hmac.SHA256, key, b"x" * 257)
        with self.assertRaises(ValueError):
            hmac.tag(42, key, b"")
        with self.assertRaises(TypeError):
            hmac.tag(hmac.SHA256, plaintext, b"")

    def test_lock_and_revoke(self):
        key = bip32.from_seed(b"\x42" * 16, "nist256p1").private_key()
        digest = b"\x5a" * 32
        for revoke in (config.lock, self.owner.destroy):
            revoke()
            for action in (
                lambda: nist256p1.sign(key, digest),
                lambda: nist256p1.publickey(key),
                lambda: hmac.tag(hmac.SHA256, key, b"message"),
            ):
                with self.assertRaises(ValueError):
                    action()
            self.assertTrue(config.unlock("", None))


if __name__ == "__main__":
    unittest.main()
