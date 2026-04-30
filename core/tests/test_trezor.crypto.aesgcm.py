# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto import aesgcm_decrypt, aesgcm_encrypt


class TestCryptoAes(unittest.TestCase):

    # test vectors from
    # https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/mac/gcmtestvectors.zip

    vectors = [
        (
            "11754cd72aec309bf52f7687212e8957",
            "3c819d9a9bed087615030b65",
            "",
            "",
            "",
            "250327c674aaf477aef2675748cf6971",
        ),
        (
            "fe9bb47deb3a61e423c2231841cfd1fb",
            "4d328eb776f500a2f7fb47aa",
            "f1cc3818e421876bb6b8bbd6c9",
            "",
            "b88c5c1977b35b517b0aeae967",
            "43fd4727fe5cdb4b5b42818dea7ef8c9",
        ),
        (
            "6f44f52c2f62dae4e8684bd2bc7d16ee7c557330305a790d",
            "9ae35825d7c7edc9a39a0732",
            "37222d30895eb95884bbbbaee4d9cae1",
            "1b4236b846fc2a0f782881ba48a067e9",
            "a54b5da33fc1196a8ef31a5321bfcaeb",
            "1c198086450ae1834dd6c2636796bce2",
        ),
        (
            "05f714021372ae1c8d72c98e6307fbddb26ee27615860a9fb48ba4c3ea360a00",
            "c0",
            "ec3afbaa1447e47ce068bffb787bd0cadc9f0deceb11fa78e981271390578ae95891f26664b5e62d1fd5fd0d0767a54da5f86f",
            "faf9fa457a8e70ea709da28545f18f041351e8d5",
            "c8c5816ba9e7e0d20820dc0064a519a277889f5ac9661c9882b5a9896fd12836c6721514e885b1d34f5e888d1d85abce8c2ebb",
            "0856f211fade7d26d64478ca46025a3c",
        ),
    ]

    def test_gcm(self):
        for vector in self.vectors:
            key, iv, pt, aad, ct, tag = map(unhexlify, vector)

            # Test encryption.
            ctx = aesgcm_encrypt(key, iv)
            if aad:
                ctx.auth(aad)
            self.assertEqual(ctx.encrypt(pt), ct)
            self.assertEqual(ctx.finish(), tag)

            # Test decryption.
            ctx = aesgcm_decrypt(key, iv)
            if aad:
                ctx.auth(aad)
            self.assertEqual(ctx.decrypt(ct), pt)
            self.assertIsNone(ctx.finish(tag))

    def test_gcm_in_place(self):
        for vector in self.vectors:
            key, iv, pt, aad, ct, tag = map(unhexlify, vector)
            buffer = bytearray(pt)

            # Test encryption.
            ctx = aesgcm_encrypt(key, iv)
            if aad:
                ctx.auth(aad)
            returned = ctx.encrypt_in_place(buffer)
            self.assertEqual(buffer, ct)
            self.assertEqual(returned, len(buffer))
            self.assertEqual(ctx.finish(), tag)

            # Test decryption.
            ctx = aesgcm_decrypt(key, iv)
            if aad:
                ctx.auth(aad)
            returned = ctx.decrypt_in_place(buffer)
            self.assertEqual(buffer, pt)
            self.assertEqual(returned, len(buffer))
            self.assertIsNone(ctx.finish(tag))

    def test_gcm_chunks(self):
        for vector in self.vectors:
            key, iv, pt, aad, ct, tag = map(unhexlify, vector)

            chunk1 = len(pt) // 3

            # Decrypt by chunks and add authenticated data by chunks.
            ctx = aesgcm_decrypt(key, iv)
            self.assertEqual(ctx.decrypt(ct[:chunk1]), pt[:chunk1])
            ctx.auth(aad[:17])
            self.assertEqual(ctx.decrypt(ct[chunk1:]), pt[chunk1:])
            ctx.auth(aad[17:])
            self.assertIsNone(ctx.finish(tag))

            # Encrypt by chunks and add authenticated data by chunks.
            ctx = aesgcm_encrypt(key, iv)
            ctx.auth(aad[:7])
            self.assertEqual(ctx.encrypt(pt[:chunk1]), ct[:chunk1])
            ctx.auth(aad[7:])
            self.assertEqual(ctx.encrypt(pt[chunk1:]), ct[chunk1:])
            self.assertEqual(ctx.finish(), tag)

    def test_gcm_chunks_in_place(self):
        for vector in self.vectors:
            key, iv, pt, aad, ct, tag = map(unhexlify, vector)
            buffer = bytearray(ct)
            chunk1_length = len(pt) // 3
            chunk2_length = len(pt) - chunk1_length

            # Decrypt by chunks and add authenticated data by chunks.
            ctx = aesgcm_decrypt(key, iv)
            returned = ctx.decrypt_in_place(memoryview(buffer)[:chunk1_length])
            self.assertEqual(returned, chunk1_length)
            ctx.auth(aad[:17])
            returned = ctx.decrypt_in_place(memoryview(buffer)[chunk1_length:])
            ctx.auth(aad[17:])
            self.assertEqual(returned, chunk2_length)
            self.assertEqual(buffer, pt)
            self.assertIsNone(ctx.finish(tag))

            # Encrypt by chunks and add authenticated data by chunks.
            ctx = aesgcm_encrypt(key, iv)
            ctx.auth(aad[:7])
            returned = ctx.encrypt_in_place(memoryview(buffer)[:chunk1_length])
            self.assertEqual(returned, chunk1_length)
            ctx.auth(aad[7:])
            returned = ctx.encrypt_in_place(memoryview(buffer)[chunk1_length:])
            self.assertEqual(returned, chunk2_length)
            self.assertEqual(buffer, ct)
            self.assertEqual(ctx.finish(), tag)

    def test_gcm_invalid_tag_len(self):
        for vector in self.vectors:
            key, iv, pt, aad, ct, _tag = map(unhexlify, vector)
            invalid_tags = [
                b"",
                b"\x00",
                _tag[:15],
                b"\x00" + _tag,
                _tag + _tag,
            ]

            for tag in invalid_tags:
                ctx = aesgcm_decrypt(key, iv)
                if aad:
                    ctx.auth(aad)
                self.assertEqual(ctx.decrypt(ct), pt)

                # Try finishing the decryption with an invalid-length tag
                with self.assertRaises(ValueError) as e:
                    ctx.finish(tag)
                self.assertEqual(
                    e.value.value,
                    "Invalid length of the tag. It has to be 16 bytes.",
                )

    def test_gcm_invalid_tag(self):
        invalid_tag = b"\xab" * 16
        for vector in self.vectors:
            key, iv, pt, aad, ct, _ = map(unhexlify, vector)
            ctx = aesgcm_decrypt(key, iv)
            if aad:
                ctx.auth(aad)
            self.assertEqual(ctx.decrypt(ct), pt)

            # Try finishing the decryption with an invalid tag
            with self.assertRaises(RuntimeError) as e:
                ctx.finish(invalid_tag)
            self.assertEqual(
                e.value.value,
                "Authentication failed.",
            )


if __name__ == "__main__":
    unittest.main()
