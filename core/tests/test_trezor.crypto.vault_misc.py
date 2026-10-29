# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import cipher_key_value, secbytes

from trezor.crypto import aes, bip32, hmac
from trezor.crypto.curve import curve25519, nist256p1, secp256k1


class TestVaultMisc(VaultTestCase):
    def test_ecdh_and_public_keys(self):
        raw = b"\x01" * 32
        key = secbytes(raw)
        for curve in (secp256k1, nist256p1, curve25519):
            peer = curve.publickey(b"\x02" * 32)
            self.assertEqual(curve.multiply(key, peer), curve.multiply(raw, peer))
            with self.assertRaises(ValueError):
                curve.multiply(key, peer[:31])
        for compressed in (False, True):
            self.assertEqual(
                secp256k1.publickey(key, compressed),
                secp256k1.publickey(raw, compressed),
            )
        self.secret_owner.destroy()
        with self.assertRaises(ValueError):
            secp256k1.multiply(key, secp256k1.publickey(raw))

    def test_key_value_vectors_and_chunks(self):
        raw = b"\x01" * 32
        node = bip32.HDNode(
            depth=0,
            fingerprint=0,
            child_num=0,
            chain_code=b"C" * 32,
            private_key=raw,
            curve_name="secp256k1",
        )
        for label in (b"", b"Enable labeling?", "label \u20ac".encode()):
            for flags in range(4):
                ask_encrypt, ask_decrypt = bool(flags & 1), bool(flags & 2)
                material = hmac(
                    hmac.SHA512,
                    raw,
                    label
                    + (b"E1" if ask_encrypt else b"E0")
                    + (b"D1" if ask_decrypt else b"D0"),
                ).digest()
                for supplied_iv in (b"", b"I" * 16):
                    iv = supplied_iv or material[32:48]
                    for length in (0, 16, 256, 272, 1024):
                        message = (b"public value data" * 64)[:length]
                        expected = aes(aes.CBC, material[:32], iv).encrypt(message)
                        encrypted = cipher_key_value(
                            node,
                            label,
                            message,
                            True,
                            ask_encrypt,
                            ask_decrypt,
                            supplied_iv,
                        )
                        self.assertEqual(encrypted, expected)
                        self.assertEqual(
                            cipher_key_value(
                                node,
                                label,
                                encrypted,
                                False,
                                ask_encrypt,
                                ask_decrypt,
                                supplied_iv,
                            ),
                            message,
                        )
        with self.assertRaises(ValueError):
            cipher_key_value(node, b"label", b"not aligned", True, False, False)
        self.secret_owner.destroy()
        with self.assertRaises(ValueError):
            cipher_key_value(node, b"label", b"A" * 16, True, False, False)


if __name__ == "__main__":
    unittest.main()
