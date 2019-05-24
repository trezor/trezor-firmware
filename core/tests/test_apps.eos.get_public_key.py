from common import *

from apps.eos.get_public_key import _get_public_key, _public_key_to_wif
from trezor.crypto import bip32, bip39
from ubinascii import hexlify, unhexlify
from apps.common.paths import HARDENED
from apps.eos.helpers import validate_full_path


class TestEosGetPublicKey(unittest.TestCase):
    def test_get_public_key_scheme(self):
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        seed = bip39.seed(mnemonic, '')

        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 194, 0x80000000, 0, 0],
            [0x80000000 | 44, 0x80000000 | 194, 0x80000000, 0, 1],
            [0x80000000 | 44, 0x80000000 | 194],
            [0x80000000 | 44, 0x80000000 | 194, 0x80000000, 0, 0x80000000],
        ]

        public_keys = [
            b'0315c358024ce46767102578947584c4342a6982b922d454f63588effa34597197',
            b'029622eff7248c4d298fe28f2df19ee0d5f7674f678844e05c31d1a5632412869e',
            b'02625f33c10399703e95e41bd5054beef3ab893dcc7df2bb9bdcee48359b29069d',
            b'037c9b7d24d42589941cca3f4debc75b37c0e7b881e6eb00d2e674958debe3bbc3',
        ]

        wif_keys = [
            'PUB_K1_6zpSNY1YoLxNt2VsvJjoDfBueU6xC1M1ERJw1UoekL1NK2aD4t',
            'PUB_K1_62cPUiWnLqbUjiBMxbEU4pm4Hp5X3RGk4KMTadvZNygjZg9L9x',
            'PUB_K1_5dp8aCFoFwrKo6KuUfos1hwMfZGkiZUbaF2CyuD4chyBEdV3mU',
            'PUB_K1_7n7TXwR4Y3DtPt2ji6akhQi5uw4SruuPArvoNJso84vhxKpEz3',
        ]

        for index, path in enumerate(derivation_paths):
            node = bip32.from_seed(seed, 'secp256k1')
            node.derive_path(path)
            wif, public_key = _get_public_key(node)

            self.assertEqual(hexlify(public_key), public_keys[index])
            self.assertEqual(wif, wif_keys[index])
            self.assertEqual(_public_key_to_wif(public_key), wif_keys[index])

    def test_paths(self):
        # 44'/194'/a'/0/0 is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 194 | HARDENED],
            [44 | HARDENED, 194 | HARDENED, 0 | HARDENED, 0, 0, 0],
            [44 | HARDENED, 194 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 194 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 194 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 194 | HARDENED, 0 | HARDENED, 0, 1],
            [44 | HARDENED, 160 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 199 | HARDENED, 0 | HARDENED, 0, 9999],
        ]
        correct_paths = [
            [44 | HARDENED, 194 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 194 | HARDENED, 9 | HARDENED, 0, 0],
            [44 | HARDENED, 194 | HARDENED, 9999 | HARDENED, 0, 0],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == '__main__':
    unittest.main()
