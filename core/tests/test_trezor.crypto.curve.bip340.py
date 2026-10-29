# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import SecretOwner, _secret_owner_activate, revoke_secrets, secbytes

from trezor import config
from trezor.crypto import random
from trezor.crypto.curve import bip340


class TestCryptoBip340(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        _secret_owner_activate(SecretOwner())

    def tearDown(self):
        revoke_secrets()

    # Test vectors from https://github.com/bitcoin/bips/blob/master/bip-0340/test-vectors.csv
    vectors = [
        (
            "0000000000000000000000000000000000000000000000000000000000000003",
            "F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9",
        ),
        (
            "B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF",
            "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
        ),
        (
            "C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9",
            "DD308AFEC5777E13121FA72B9CC1B7CC0139715309B086C960E18FD969774EB8",
        ),
        (
            "0B432B2677937381AEF05BB02A66ECD012773062CF3FA2549E44F58ED2401710",
            "25D1DFF95105F5253C4022F628A996AD3A0D95FBF21D468A1B33F8C160D8F517",
        ),
    ]

    def test_generate_secret(self):
        for _ in range(100):
            sk = bip340.generate_secret()
            self.assertIsInstance(sk, secbytes)
            with self.assertRaises(TypeError):
                bytes(sk)
            self.assertTrue(bip340.verify_publickey(bip340.publickey(sk)))

    def test_publickey(self):
        for sk, pk in self.vectors:
            pk_computed = bip340.publickey(bytes.fromhex(sk)).hex()
            self.assertEqual(str(pk_computed).upper(), pk)

    def test_sign_verify_random(self):
        for _ in range(100):
            sk = bip340.generate_secret()
            pk = bip340.publickey(sk)
            dig = random.bytes(32)
            sig = bip340.sign(sk, dig)
            self.assertTrue(bip340.verify(pk, sig, dig))

    def test_tweak_stays_opaque_and_preserves_source(self):
        key = bip340.generate_secret()
        digest = b"\x42" * 32
        original_public = bip340.publickey(key)
        original_signature = bip340.sign(key, digest)
        for root in (None, b"\x24" * 32):
            tweaked = bip340.tweak_secret_key(key, root)
            self.assertIsInstance(tweaked, secbytes)
            with self.assertRaises(TypeError):
                memoryview(tweaked)
            expected_public = bip340.tweak_public_key(original_public, root)
            self.assertEqual(bip340.publickey(tweaked), expected_public)
            self.assertTrue(
                bip340.verify(expected_public, bip340.sign(tweaked, digest), digest)
            )
            self.assertEqual(bip340.publickey(key), original_public)
            self.assertEqual(bip340.sign(key, digest), original_signature)
            key.destroy()
            self.assertTrue(
                bip340.verify(expected_public, bip340.sign(tweaked, digest), digest)
            )
            tweaked.destroy()
            with self.assertRaises(ValueError):
                bip340.sign(tweaked, digest)
            key = secbytes(bytes.fromhex(self.vectors[0][0]))
            original_public = bip340.publickey(key)
            original_signature = bip340.sign(key, digest)

    def test_revocation_and_errors(self):
        key = bip340.generate_secret()
        for invalid in (b"", b"x" * 31, b"x" * 33):
            with self.assertRaises(ValueError):
                bip340.sign(key, invalid)
            with self.assertRaises(ValueError):
                bip340.tweak_secret_key(key, invalid)
        revoke_secrets()
        for action in (
            lambda: bip340.sign(key, b"x" * 32),
            lambda: bip340.publickey(key),
            lambda: bip340.tweak_secret_key(key),
        ):
            with self.assertRaises(ValueError):
                action()


if __name__ == "__main__":
    unittest.main()
