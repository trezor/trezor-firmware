from common import *

from apps.cardano.get_public_key import _get_public_key
from trezor.crypto import bip32
from ubinascii import hexlify


class TestCardanoGetPublicKey(unittest.TestCase):
    def test_get_public_key_scheme(self):
        mnemonic = "all all all all all all all all all all all all"
        node = bip32.from_mnemonic_cardano(mnemonic)

        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000],
            [0x80000000 | 44, 0x80000000 | 1815],
            [0x80000000 | 44, 0x80000000 | 1815, 0, 0, 0],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0],
        ]

        public_keys = [
            b'a938c8554ae04616cfaae7cd0eb557475082c4e910242ce774967e0bd7492408',
            b'8c47ebce34234d04fd3dfbac33feaba6133e4e3d77c4b5ab18120ec6878ad4ce',
            b'17cc0bf978756d0d5c76f931629036a810c61801b78beecb44555773d13e3791',
            b'b90fb812a2268e9569ff1172e8daed1da3dc7e72c7bded7c5bcb7282039f90d5',
        ]

        chain_codes = [
            b'cbf6ab47c8eb1a0477fc40b25dbb6c4a99454edb97d6fe5acedd3e238ef46fe0',
            b'02ac67c59a8b0264724a635774ca2c242afa10d7ab70e2bf0a8f7d4bb10f1f7a',
            b'646ac4a6295326bae6831be05921edfbcb362de48dfd37b12e74c227dfad768d',
            b'fd8e71c1543de2cdc7f7623130c5f2cceb53549055fa1f5bc88199989e08cce7',
        ]

        xpub_keys = [
            'a938c8554ae04616cfaae7cd0eb557475082c4e910242ce774967e0bd7492408cbf6ab47c8eb1a0477fc40b25dbb6c4a99454edb97d6fe5acedd3e238ef46fe0',
            '8c47ebce34234d04fd3dfbac33feaba6133e4e3d77c4b5ab18120ec6878ad4ce02ac67c59a8b0264724a635774ca2c242afa10d7ab70e2bf0a8f7d4bb10f1f7a',
            '17cc0bf978756d0d5c76f931629036a810c61801b78beecb44555773d13e3791646ac4a6295326bae6831be05921edfbcb362de48dfd37b12e74c227dfad768d',
            'b90fb812a2268e9569ff1172e8daed1da3dc7e72c7bded7c5bcb7282039f90d5fd8e71c1543de2cdc7f7623130c5f2cceb53549055fa1f5bc88199989e08cce7',
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(node, derivation_path)

            self.assertEqual(hexlify(key.node.public_key), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])


if __name__ == '__main__':
    unittest.main()
