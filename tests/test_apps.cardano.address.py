from common import *
from apps.common import seed
from trezor import wire

from apps.cardano.address import (
    _derive_hd_passphrase,
    _encrypt_derivation_path,
    _get_address_root,
    _address_hash,
    validate_derivation_path,
    derive_address_and_node
)
from trezor.crypto import bip32


class TestCardanoAddress(unittest.TestCase):
    def test_hardened_address_derivation(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        node = bip32.from_mnemonic_cardano(mnemonic)

        addresses = [
            "DdzFFzCqrhtDB6YEgPQqFiVnhKsfyEMe9MLQabhayVUL2WRN1dbLLFS7VfKYBy8n3uemZRcDyqMnv7STCU9vj2eAR8CgFgKMDG2mkQN7",
            "DdzFFzCqrhtCGRQ2UYpcouvRgDnPsAYpmzWVtd5YLvaRrMAMoDmYsKhNMAWePbK7a1XbZ8ghTeyaSLZ2488extnB5F9SwHus4UFaFwkS",
            "DdzFFzCqrhsqHyZLVLeFrgcxUrPA5YMJJRJCxkESHcPkV1EuuDKhKkJNPkEyrWXhPbuMHxSnz1cNYUCN8tJsLwaFiSxMz3ab19GEvaNP",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i'
            address, _ = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000 + i])
            self.assertEqual(expected, address)

        nodes = [
            (
                "d4dd69a2f2a6374f3733f53e03f610d73dd4f1d5131169bc144e6d34c9bcbe04",
                "21d97a697583630e2cef01e5fc1555ea4fd9625ff8fcde1fc72e67aa42f975ec",
                "2df46e04ebf0816e242bfaa1c73e5ebe8863d05d7a96c8aac16f059975e63f30",
                "057658de1308930ad4a5663e4f77477014b04954a9d488e62d73b04fc659a35c"
            ),
            (
                "3476630290051477e4cc206fd5f6587065d3c9558c9891cc1c0ed5a408d5b60c",
                "3f1d4beaefd2ffff59a45cb75519960d02f4de62c076a165bc39a7d7b1fec168",
                "35b0cc0b770e04d86a9cddb0e2068b3a242f6b6e93c9a9d3c4f0899bd62b4266",
                "35bb811c631b3db3b10559bc15821a39969654ebcad80cedf544ac8bf2a73ce7"
            ),
            (
                "06a6f53baf84ac6713cd1c441081dff00d1c4abee33091dc5c5ebdec2044270c",
                "4978871e479a3a58adabb030565162832c63a2909442d306c96eaf03823ff5c9",
                "9f26aad725aef1bb0609085f2c961b4d2579bceccfb1b01f3c7d1dbdd02b50b1",
                "70f72ce51d0c984c4bbddd0297f4ffe0b4710c2c3f9a7e17f7d7e3e1810b5c33"
            ),
        ]

        for i, (priv, ext, pub, chain) in enumerate(nodes):
            _, n = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000 + i])
            self.assertEqual(unhexlify(priv), n.private_key())
            self.assertEqual(unhexlify(ext), n.private_key_ext())
            self.assertEqual(unhexlify(pub), seed.remove_ed25519_prefix(n.public_key()))
            self.assertEqual(unhexlify(chain), n.chain_code())

    def test_non_hardened_address_derivation(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        node = bip32.from_mnemonic_cardano(mnemonic)

        addresses = [
            "2w1sdSJu3GVezU6nw8LodErz7kSrEQ9hKQhsGLWk4JxTCxg7tkJvSowGKLFE7PMxknbkuYjtaWbpnJLhJgwmwNA98GPX2SGSN1t",
            "2w1sdSJu3GVg7mRbtq2aGUFKxXnpFoP9hesA1n7KJrnQ9QEgyy7DGbLU52L2cytPqCoNNhkvRCF9ZsBLwMv1E35CVh6XBiWj2GE",
            "2w1sdSJu3GVg193D2yhiiH947J9UwrbPAmNao6ciAZi3GeU7sG1D3fTAnQakzHSe1FVyuRdUjcx52Q7575LxBBNE8aCunKFA4kA",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i
            address, _ = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(expected, address)

        nodes = [
            (
                "a75a851505db79ee8557a8cb3ef561ab7d6bd24d7cc0e97b8496654431fc2e0c",
                "21fa8154e009a46a1c44709fe23b75735c8abc6256c44cc3c208c1c914f037ce",
                "723fdc0eb1300fe7f2b9b6989216a831835a88695ba2c2d5c50c8470b7d1b239",
                "ae09010e921de259b02f34ce7fd76f9c09ad224d436fe8fa38aa212177937ffe"
            ),
            (
                "48ded246510a563f759fde920016ad1356238ab5936869e45ccec5b4d8fcce0c",
                "0216c5c777bfe196576b776bd9faf2ac1318966c820edb203754166d5a0f4d92",
                "6dc82a0d40257cfc1ea5d728c6ccfa52ad5673c2dc4cfed239dff642d29fbc46",
                "cd490ae08bd2ff18e8b61c39173f6bf0db85709130baa103b9f00e4160ec150f"
            ),
            (
                "8e651d540f55a4670bb5ec8cd0812731ce734a1e745059c4f445fd8cd8fcb604",
                "ab7f8d9e7927a1a71b7b08eb3b871246dc4717d9e309b7682df0eee202a5a97a",
                "e55323d6881ca92a0816695def558145ef22f0d0c4f6133aab7a8a3f2f98ef78",
                "6c9313fcf93b55a977184514aefa1c778c1abadb2ba9f2c1351b587b7c1e1572"
            ),
        ]

        for i, (priv, ext, pub, chain) in enumerate(nodes):
            _, n = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(unhexlify(priv), n.private_key())
            self.assertEqual(unhexlify(ext), n.private_key_ext())
            self.assertEqual(unhexlify(pub), seed.remove_ed25519_prefix(n.public_key()))
            self.assertEqual(unhexlify(chain), n.chain_code())


    def test_root_address_derivation(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        node = bip32.from_mnemonic_cardano(mnemonic)

        # 44'/1815'
        address, _ = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815])
        self.assertEqual("Ae2tdPwUPEYygPo2ZNZ7Ve6ZExaFZvkGcQFZ5oSyqVNoJn5J65Foyz2XiSU", address)

        priv, ext, pub, chain = (
            "90bc16ad766aebce31b407f111db3ba95de2780c5bb760f3333dac1b3823ee53",
            "10f20917dcfa2b3c295386413ae3564365e4a51f063da644d0945f4d3da57699",
            "7d1de3f22f53904d007ff833fadd7cd6482ea1e83918b985b4ea33e63c16d183",
            "7a04a6aab0ed12af562a26db4d10344454274d0bfa6e3581df1dc02f13c5fbe5"
        )

        _, n = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815])
        self.assertEqual(unhexlify(priv), n.private_key())
        self.assertEqual(unhexlify(ext), n.private_key_ext())
        self.assertEqual(unhexlify(pub), seed.remove_ed25519_prefix(n.public_key()))
        self.assertEqual(unhexlify(chain), n.chain_code())

    def test_validate_derivation_path(self):
        incorrect_derivation_paths = [
            [0x80000000 | 44],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815],
            [0x80000000 | 43, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815],
            [0x80000000 | 44, 0x80000000 | 1816, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815],
        ]

        correct_derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815, 0x80000000 | 1815],
            [0x80000000 | 44, 0x80000000 | 1815],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000],
            [0x80000000 | 44, 0x80000000 | 1815, 0],
            [0x80000000 | 44, 0x80000000 | 1815, 0, 0],
        ]

        for derivation_path in incorrect_derivation_paths:
            self.assertRaises(wire.ProcessError, validate_derivation_path, derivation_path)

        for derivation_path in correct_derivation_paths:
            self.assertEqual(derivation_path, validate_derivation_path(derivation_path))

    def test_derive_hd_passphrase(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        root_node = bip32.from_mnemonic_cardano(mnemonic)

        self.assertEqual(hexlify(_derive_hd_passphrase(root_node)).decode('utf8'), "8ee689a22e1ec569d2ada515c4ee712ad089901b7fe0afb94fe196de944ee814")

    def test_encrypt_derivation_path(self):
        encrypted_path = _encrypt_derivation_path([0x80000000, 0x80000000], unhexlify("8ee689a22e1ec569d2ada515c4ee712ad089901b7fe0afb94fe196de944ee814"))
        self.assertEqual(hexlify(encrypted_path).decode('utf8'), "722c7a75813fafde9ff9e6d4dec19adfd57f0d20194fa4c703770020")

        encrypted_path = _encrypt_derivation_path([0x80000000, 0], unhexlify("8ee689a22e1ec569d2ada515c4ee712ad089901b7fe0afb94fe196de944ee814"))
        self.assertEqual(hexlify(encrypted_path).decode('utf8'), "722c7a75813fb5a13d916748b3fb0561c5c7b59f9bc644ea")

    def test_get_address_root(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        root_node = bip32.from_mnemonic_cardano(mnemonic)

        address_root = _get_address_root(root_node, {1: b'X\x1cr,zu\x81?\xaf\xde\x9f\xf9\xe4\xd4\x90\xadH$\xe9\xf3\x88\x16\xcb\xd2)\x02M\x0c#\xde'})
        self.assertEqual(address_root, b'\xca\x9bbQ\xa5\xaa}\x01U\xba\xe5\xa5\xaa~\x84M\x0b;\x1dM\xd8z\xe7Y\x01\xc8\x92\x91')

    def test_address_hash(self):
        data = [0, [0, b"}\x1d\xe3\xf2/S\x90M\x00\x7f\xf83\xfa\xdd|\xd6H.\xa1\xe89\x18\xb9\x85\xb4\xea3\xe6<\x16\xd1\x83z\x04\xa6\xaa\xb0\xed\x12\xafV*&\xdbM\x104DT'M\x0b\xfan5\x81\xdf\x1d\xc0/\x13\xc5\xfb\xe5"], {}]
        result = _address_hash(data)

        self.assertEqual(result, b'\x1c\xca\xee\xc9\x80\xaf}\xb0\x9a\xa8\x96E\xd6\xa4\xd1\xb4\x13\x85\xb9\xc2q\x1d5/{\x12"\xca')


if __name__ == '__main__':
    unittest.main()
