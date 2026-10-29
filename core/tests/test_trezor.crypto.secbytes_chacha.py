# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import secbytes, vault_chacha

from trezor.crypto import AuthenticationError, chacha20poly1305_encrypt


class TestVaultChaCha(VaultTestCase):
    def test_chunk_boundaries_and_authentication(self):
        key = b"K" * 32
        nonce = b"N" * 12
        aad = b"A" * 32
        opaque = secbytes(key)
        for length in (1, 63, 64, 65, 255, 256, 257, 1024):
            message = (b"public credential data" * 50)[:length]
            reference = chacha20poly1305_encrypt(key, nonce)
            reference.auth(aad)
            expected = reference.encrypt(message)
            expected_tag = reference.finish()
            encrypted, tag = vault_chacha(opaque, nonce, message, aad)
            self.assertEqual(encrypted, expected)
            self.assertEqual(tag, expected_tag)
            decrypted, _ = vault_chacha(opaque, nonce, encrypted, aad, tag, True)
            self.assertEqual(decrypted, message)
            with self.assertRaises(AuthenticationError):
                vault_chacha(opaque, nonce, encrypted, b"B" * 32, tag, True)
            tampered = bytes([encrypted[0] ^ 1]) + encrypted[1:]
            with self.assertRaises(AuthenticationError):
                vault_chacha(opaque, nonce, tampered, aad, tag, True)
            with self.assertRaises(AuthenticationError):
                vault_chacha(opaque, nonce, encrypted, aad, bytes(16), True)
        # Without AAD, as for credentials before their RP ID is known.
        reference = chacha20poly1305_encrypt(key, nonce)
        expected = reference.encrypt(b"no aad")
        tag = reference.finish()
        decrypted, _ = vault_chacha(opaque, nonce, expected, b"", tag, True)
        self.assertEqual(decrypted, b"no aad")
        self.secret_owner.destroy()
        with self.assertRaises(ValueError):
            vault_chacha(opaque, nonce, b"revoked", aad)


if __name__ == "__main__":
    unittest.main()
