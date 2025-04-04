# flake8: noqa: F403,F405
from common import *  # isort:skip
from trezorcrypto import aesgcm, curve25519

import storage

if utils.USE_THP:
    import thp_common
    from trezor.wire.thp import crypto
    from trezor.wire.thp.crypto import IV_1, IV_2, Handshake

    def get_dummy_device_secret():
        return b"\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08"


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolCrypto(unittest.TestCase):
    if utils.USE_THP:
        handshake = Handshake()
        key_1 = b"\x00\x01\x02\x03\x04\x05\x06\x07\x00\x01\x02\x03\x04\x05\x06\x07\x00\x01\x02\x03\x04\x05\x06\x07\x00\x01\x02\x03\x04\x05\x06\x07"
        # 0:key, 1:nonce, 2:auth_data, 3:plaintext, 4:expected_ciphertext, 5:expected_tag
        vectors_enc = [
            (
                key_1,
                0,
                b"\x55\x64",
                b"\x00\x01\x02\x03\x04\05\x06\x07\x08\x09",
                b"e2c9dd152fbee5821ea7",
                b"10625812de81b14a46b9f1e5100a6d0c",
            ),
            (
                key_1,
                1,
                b"\x55\x64",
                b"\x00\x01\x02\x03\x04\05\x06\x07\x08\x09",
                b"79811619ddb07c2b99f8",
                b"71c6b872cdc499a7e9a3c7441f053214",
            ),
            (
                key_1,
                369,
                b"\x55\x64",
                b"\x00\x01\x02\x03\x04\05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",
                b"03bd030390f2dfe815a61c2b157a064f",
                b"c1200f8a7ae9a6d32cef0fff878d55c2",
            ),
            (
                key_1,
                369,
                b"\x55\x64\x73\x82\x91",
                b"\x00\x01\x02\x03\x04\05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",
                b"03bd030390f2dfe815a61c2b157a064f",
                b"693ac160cd93a20f7fc255f049d808d0",
            ),
        ]
        # 0:chaining key, 1:input, 2:output_1, 3:output:2
        vectors_hkdf = [
            (
                crypto.PROTOCOL_NAME,
                b"\x01\x02",
                b"c784373a217d6be057cddc6068e6748f255fc8beb6f99b7b90cbc64aad947514",
                b"12695451e29bf08ffe5e4e6ab734b0c3d7cdd99b16cd409f57bd4eaa874944ba",
            ),
            (
                b"\xc7\x84\x37\x3a\x21\x7d\x6b\xe0\x57\xcd\xdc\x60\x68\xe6\x74\x8f\x25\x5f\xc8\xbe\xb6\xf9\x9b\x7b\x90\xcb\xc6\x4a\xad\x94\x75\x14",
                b"\x31\x41\x59\x26\x52\x12\x34\x56\x78\x89\x04\xaa",
                b"f88c1e08d5c3bae8f6e4a3d3324c8cbc60a805603e399e69c4bf4eacb27c2f48",
                b"5f0216bdb7110ee05372286974da8c9c8b96e2efa15b4af430755f462bd79a76",
            ),
        ]
        vectors_iv = [
            (0, b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"),
            (1, b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"),
            (7, b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07"),
            (1025, b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x01"),
            (4294967295, b"\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff"),
            (0xFFFFFFFFFFFFFFFF, b"\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff"),
        ]

    def __init__(self):
        if __debug__:
            thp_common.suppres_debug_log()
        super().__init__()

    def setUp(self):
        utils.DISABLE_ENCRYPTION = False

    def test_encryption(self):
        for v in self.vectors_enc:
            buffer = bytearray(v[3])
            tag = crypto.enc(buffer, v[0], v[1], v[2])
            self.assertEqual(hexlify(buffer), v[4])
            self.assertEqual(hexlify(tag), v[5])
            self.assertTrue(crypto.dec(buffer, tag, v[0], v[1], v[2]))
            self.assertEqual(buffer, v[3])

    def test_hkdf(self):
        for v in self.vectors_hkdf:
            ck, k = crypto._hkdf(v[0], v[1])
            self.assertEqual(hexlify(ck), v[2])
            self.assertEqual(hexlify(k), v[3])

    def test_iv_from_nonce(self):
        for v in self.vectors_iv:
            # x = v[0]
            # y = x.to_bytes(8, "big")
            iv = crypto._get_iv_from_nonce(v[0])
            self.assertEqual(iv, v[1])
        with self.assertRaises(AssertionError) as e:
            iv = crypto._get_iv_from_nonce(0xFFFFFFFFFFFFFFFF + 1)
        self.assertEqual(e.value.value, "Nonce overflow, terminate the channel")

    def test_incorrect_vectors(self):
        pass

    def test_th1_crypto(self):
        storage.device.get_device_secret = get_dummy_device_secret
        handshake = self.handshake

        host_ephemeral_privkey = curve25519.generate_secret()
        host_ephemeral_pubkey = curve25519.publickey(host_ephemeral_privkey)
        handshake.handle_th1_crypto(b"", host_ephemeral_pubkey)

    def test_th2_crypto(self):
        handshake = self.handshake

        host_static_privkey = curve25519.generate_secret()
        host_static_pubkey = curve25519.publickey(host_static_privkey)
        aes_ctx = aesgcm(handshake.k, IV_2)
        aes_ctx.auth(handshake.h)
        encrypted_host_static_pubkey = bytearray(
            aes_ctx.encrypt(host_static_pubkey) + aes_ctx.finish()
        )

        # Code to encrypt Host's noise encrypted payload correctly:
        protomsg = bytearray(b"\x10\x02\x10\x03")
        temp_k = handshake.k
        temp_h = handshake.h

        temp_h = crypto._hash_of_two(temp_h, encrypted_host_static_pubkey)
        _, temp_k = crypto._hkdf(
            handshake.ck,
            curve25519.multiply(handshake.trezor_ephemeral_privkey, host_static_pubkey),
        )
        aes_ctx = aesgcm(temp_k, IV_1)
        aes_ctx.encrypt_in_place(protomsg)
        aes_ctx.auth(temp_h)
        tag = aes_ctx.finish()
        encrypted_payload = bytearray(protomsg + tag)
        # end of encrypted payload generation

        handshake.handle_th2_crypto(encrypted_host_static_pubkey, encrypted_payload)
        self.assertEqual(encrypted_payload[:4], b"\x10\x02\x10\x03")


if __name__ == "__main__":
    unittest.main()
