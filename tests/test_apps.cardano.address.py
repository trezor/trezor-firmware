from common import *
from apps.common import seed
from trezor import wire

from apps.cardano.address import (
    _get_address_root,
    _address_hash,
    validate_derivation_path,
    derive_address_and_node
)
from trezor.crypto import bip32


class TestCardanoAddress(unittest.TestCase):
    def test_hardened_address_derivation_scheme(self):
        mnemonic = "all all all all all all all all all all all all"
        node = bip32.from_mnemonic_cardano(mnemonic)

        addresses = [
            "Ae2tdPwUPEZ98eHFwxSsPBDz73amioKpr58Vw85mP1tMkzq8siaftiejJ3j",
            "Ae2tdPwUPEZKA971NCHuHqaEnxZDFWPzH3fEsLpDnbEpG6UeMRHnRzCzEwK",
            "Ae2tdPwUPEZL9Ag1ouS4b1zjuPxKpvEUgjpVpG1KQFs5pNewQb65F1WXVQ2",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i'
            address, _ = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000 + i])
            self.assertEqual(expected, address)

        nodes = [
            (
                b"3881a8de77d069001010d7f7d5211552e7d539b0e253add710367f95e528ed51",
                b"9b77608b38e0a0c7861aa234557c81482f42aae2d17993a8ddaec1868fb04d60",
                b"a938c8554ae04616cfaae7cd0eb557475082c4e910242ce774967e0bd7492408",
                b"cbf6ab47c8eb1a0477fc40b25dbb6c4a99454edb97d6fe5acedd3e238ef46fe0"
            ),
            (
                b"3003aca659846540b9ed04f2b844f2d8ea964856ca38a7dffedef4f6e528ed51",
                b"8844ccc81d633e1c7126f30c2524c1652617cf58da755014070215bf5070ba38",
                b"be28c00ed6cb9b70310f78028f8e3a2db935baf482d84afa590b0b5b864571cc",
                b"584b4631d752023a249e980779517280e6c0b3ac7a7f27c6e9456bfd228ca60b"
            ),
            (
                b"68e4482add0a741e14c8f2306bf83206a623e3729dd24175915eedece428ed51",
                b"3165a80c5efe846224d46a0427cdb2be4f31ea3585c51f4131faefc4328ad95a",
                b"9a32499976ffb582daa9988dfc42a303de5ed00c320c929f496be3c6eb1cf405",
                b"da07ca30a3d1c5fe3c34ce5fa197722446a646624a10bdf8889a4b9c347b2ef2"
            ),
        ]

        for i, (priv, ext, pub, chain) in enumerate(nodes):
            _, n = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000 + i])
            self.assertEqual(hexlify(n.private_key()), priv)
            self.assertEqual(hexlify(n.private_key_ext()), ext)
            self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
            self.assertEqual(hexlify(n.chain_code()), chain)

    def test_non_hardened_address_derivation_scheme(self):
        mnemonic = "all all all all all all all all all all all all"
        node = bip32.from_mnemonic_cardano(mnemonic)

        addresses = [
            "Ae2tdPwUPEZ5YUb8sM3eS8JqKgrRLzhiu71crfuH2MFtqaYr5ACNRdsswsZ",
            "Ae2tdPwUPEZJb8r1VZxweSwHDTYtqeYqF39rZmVbrNK62JHd4Wd7Ytsc8eG",
            "Ae2tdPwUPEZFm6Y7aPZGKMyMAK16yA5pWWKU9g73ncUQNZsAjzjhszenCsq",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i
            address, _ = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(address, expected)

        nodes = [
            (
                b"d03ba81163fd55af97bd132bf651a0da5b5e6201b15b1caca60b0be8e028ed51",
                b"493f44aa8d25fe0d3fe2935c76ea6b3e9e41c79e9dbcbe7131357c5aa1b6cac5",
                b"b90fb812a2268e9569ff1172e8daed1da3dc7e72c7bded7c5bcb7282039f90d5",
                b"fd8e71c1543de2cdc7f7623130c5f2cceb53549055fa1f5bc88199989e08cce7"
            ),
            (
                b"08b6438c8dd49d34b71c8e914d6ac3184e5ab3dcc8af023d08503a7edf28ed51",
                b"3fee605fdfaddc1ee2ea0b246b02c9abc54ad741054bc83943e8b21487b5a053",
                b"89053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea",
                b"26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a635"
            ),
            (
                b"088f0275bf4a1bd18f08d7ef06c6ddb6ce7e3dc415fb4e89fe21bf39e628ed51",
                b"4c44563c7df519ea9b4d1801c1ab98b449db28b87f1c3837759c20f68c4c1e65",
                b"52548cb98e6f46a592bdf7f3598a9abc0126c78dfa3f46d1894ee52a5213e833",
                b"91af0668ee449e613e61bbb2482e5ddee1d9b15785727ec3e362c36861bff923"
            ),
        ]

        for i, (priv, ext, pub, chain) in enumerate(nodes):
            _, n = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(hexlify(n.private_key()), priv)
            self.assertEqual(hexlify(n.private_key_ext()), ext)
            self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
            self.assertEqual(hexlify(n.chain_code()), chain)


    def test_root_address_derivation_scheme(self):
        mnemonic = "all all all all all all all all all all all all"
        node = bip32.from_mnemonic_cardano(mnemonic)

        # 44'/1815'
        address, _ = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815])
        self.assertEqual(address, "Ae2tdPwUPEZ2FGHX3yCKPSbSgyuuTYgMxNq652zKopxT4TuWvEd8Utd92w3")

        priv, ext, pub, chain = (
            b"204ec79cbb6502a141de60d274962010c7f1c94a2987b26506433184d228ed51",
            b"975cdd1c8610b44701567f05934c45c8716064263ccfe72ed2167ccb705c09b6",
            b"8c47ebce34234d04fd3dfbac33feaba6133e4e3d77c4b5ab18120ec6878ad4ce",
            b"02ac67c59a8b0264724a635774ca2c242afa10d7ab70e2bf0a8f7d4bb10f1f7a"
        )

        _, n = derive_address_and_node(node, [0x80000000 | 44, 0x80000000 | 1815])
        self.assertEqual(hexlify(n.private_key()), priv)
        self.assertEqual(hexlify(n.private_key_ext()), ext)
        self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
        self.assertEqual(hexlify(n.chain_code()), chain)


    def test_address_hash(self):
        data = [0, [0, b"}\x1d\xe3\xf2/S\x90M\x00\x7f\xf83\xfa\xdd|\xd6H.\xa1\xe89\x18\xb9\x85\xb4\xea3\xe6<\x16\xd1\x83z\x04\xa6\xaa\xb0\xed\x12\xafV*&\xdbM\x104DT'M\x0b\xfan5\x81\xdf\x1d\xc0/\x13\xc5\xfb\xe5"], {}]
        result = _address_hash(data)

        self.assertEqual(result, b'\x1c\xca\xee\xc9\x80\xaf}\xb0\x9a\xa8\x96E\xd6\xa4\xd1\xb4\x13\x85\xb9\xc2q\x1d5/{\x12"\xca')


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

    def test_get_address_root_scheme(self):
        mnemonic = "all all all all all all all all all all all all"
        root_node = bip32.from_mnemonic_cardano(mnemonic)

        address_root = _get_address_root(root_node, {1: b'X\x1cr,zu\x81?\xaf\xde\x9f\xf9\xe4\xd4\x90\xadH$\xe9\xf3\x88\x16\xcb\xd2)\x02M\x0c#\xde'})
        self.assertEqual(address_root, b'\xb3\xbbS\xa8;uN:E=\xe8\xe5\x9c\x18\xbcn\xcf\xd0c\xba\x0e\xba\xaelL}\xba\xbb')

if __name__ == '__main__':
    unittest.main()
