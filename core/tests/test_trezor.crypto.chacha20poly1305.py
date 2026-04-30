# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto import chacha20poly1305_decrypt, chacha20poly1305_encrypt


class TestCryptoChaCha20Poly1305(unittest.TestCase):

    vectors = [
        # from https://github.com/wg/c20p1305/blob/master/rfc7539_test.c
        (
            "4c616469657320616e642047656e746c656d656e206f662074686520636c617373206f66202739393a204966204920636f756c64206f6666657220796f75206f6e6c79206f6e652074697020666f7220746865206675747572652c2073756e73637265656e20776f756c642062652069742e",
            "50515253c0c1c2c3c4c5c6c7",
            "808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f",
            "070000004041424344454647",
            "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d63dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b3692ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc3ff4def08e4b7a9de576d26586cec64b6116",
            "1ae10b594f09e26a7e902ecbd0600691",
        ),
        # from https://tools.ietf.org/html/rfc7539#appendix-A.5
        (
            "496e7465726e65742d4472616674732061726520647261667420646f63756d656e74732076616c696420666f722061206d6178696d756d206f6620736978206d6f6e74687320616e64206d617920626520757064617465642c207265706c616365642c206f72206f62736f6c65746564206279206f7468657220646f63756d656e747320617420616e792074696d652e20497420697320696e617070726f70726961746520746f2075736520496e7465726e65742d447261667473206173207265666572656e6365206d6174657269616c206f7220746f2063697465207468656d206f74686572207468616e206173202fe2809c776f726b20696e2070726f67726573732e2fe2809d",
            "f33388860000000000004e91",
            "1c9240a5eb55d38af333888604f6b5f0473917c1402b80099dca5cbc207075c0",
            "000000000102030405060708",
            "64a0861575861af460f062c79be643bd5e805cfd345cf389f108670ac76c8cb24c6cfc18755d43eea09ee94e382d26b0bdb7b73c321b0100d4f03b7f355894cf332f830e710b97ce98c8a84abd0b948114ad176e008d33bd60f982b1ff37c8559797a06ef4f0ef61c186324e2b3506383606907b6a7c02b0f9f6157b53c867e4b9166c767b804d46a59b5216cde7a4e99040c5a40433225ee282a1b0a06c523eaf4534d7f83fa1155b0047718cbc546a0d072b04b3564eea1b422273f548271a0bb2316053fa76991955ebd63159434ecebb4e466dae5a1073a6727627097a1049e617d91d361094fa68f0ff77987130305beaba2eda04df997b714d6c6f2c29a6ad5cb4022b02709b",
            "eead9d67890cbb22392336fea1851f38",
        ),
    ]

    def test_chacha20_encrypt(self):
        for vector in self.vectors:
            plaintext, _, key, nonce, ciphertext, _ = map(unhexlify, vector)

            ctx = chacha20poly1305_encrypt(key, nonce)
            out = ctx.encrypt(plaintext)
            self.assertEqual(out, ciphertext)

    def test_chacha20_decrypt(self):
        for vector in self.vectors:
            plaintext, _, key, nonce, ciphertext, _ = map(unhexlify, vector)
            ctx = chacha20poly1305_decrypt(key, nonce)
            out = ctx.decrypt(ciphertext)
            self.assertEqual(out, plaintext)

    def test_chacha20poly1305_encrypt_mac(self):
        for vector in self.vectors:
            plaintext, aad, key, nonce, ciphertext, tag = map(unhexlify, vector)

            ctx = chacha20poly1305_encrypt(key, nonce)
            ctx.auth(aad)
            out = ctx.encrypt(plaintext)
            self.assertEqual(out, ciphertext)
            out = ctx.finish()
            self.assertEqual(out, tag)

    def test_chacha20poly1305_decrypt_mac(self):
        for vector in self.vectors:
            plaintext, aad, key, nonce, ciphertext, tag = map(unhexlify, vector)

            ctx = chacha20poly1305_decrypt(key, nonce)
            ctx.auth(aad)
            out = ctx.decrypt(ciphertext)
            self.assertEqual(out, plaintext)
            self.assertIsNone(ctx.finish(tag))

    def test_chacha20poly1305_invalid_mac_len(self):
        for vector in self.vectors:
            _, aad, key, nonce, ciphertext, _mac = map(unhexlify, vector)
            invalid_macs = [
                b"",
                b"\x00",
                _mac[:15],
                b"\x00" + _mac,
                _mac + _mac,
            ]
            for mac in invalid_macs:
                ctx = chacha20poly1305_decrypt(key, nonce)
                ctx.auth(aad)
                ctx.decrypt(ciphertext)
                with self.assertRaises(ValueError) as e:
                    ctx.finish(mac)
                self.assertEqual(
                    e.value.value,
                    "Invalid length of the expected mac. It has to be 16 bytes.",
                )

    def test_chacha20poly1305_invalid_mac(self):
        invalid_mac = b"\xab" * 16
        for vector in self.vectors:
            _, aad, key, nonce, ciphertext, _ = map(unhexlify, vector)

            ctx = chacha20poly1305_decrypt(key, nonce)
            ctx.auth(aad)
            ctx.decrypt(ciphertext)
            with self.assertRaises(RuntimeError) as e:
                ctx.finish(invalid_mac)
            self.assertEqual(e.value.value, "Authentication failed.")


if __name__ == "__main__":
    unittest.main()
