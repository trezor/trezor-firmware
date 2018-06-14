from common import *

from apps.cardano.get_public_key import _get_public_key
from trezor.crypto import bip32
from ubinascii import hexlify


class TestCardanoGetPublicKey(unittest.TestCase):
    def test_get_public_key(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        node = bip32.from_mnemonic_cardano(mnemonic)

        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000],
            [0x80000000 | 44, 0x80000000 | 1815],
            [0x80000000 | 44, 0x80000000 | 1815, 0, 0, 0],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0],
        ]

        root_hd_passphrase = '8ee689a22e1ec569d2ada515c4ee712ad089901b7fe0afb94fe196de944ee814'

        public_keys = [
            '2df46e04ebf0816e242bfaa1c73e5ebe8863d05d7a96c8aac16f059975e63f30',
            '7d1de3f22f53904d007ff833fadd7cd6482ea1e83918b985b4ea33e63c16d183',
            'f59a28d704df090d8fc641248bdb27d0d001da13ddb332a79cfba8a9fa7233e7',
            '723fdc0eb1300fe7f2b9b6989216a831835a88695ba2c2d5c50c8470b7d1b239',
        ]

        chain_codes = [
            '057658de1308930ad4a5663e4f77477014b04954a9d488e62d73b04fc659a35c',
            '7a04a6aab0ed12af562a26db4d10344454274d0bfa6e3581df1dc02f13c5fbe5',
            '7f01fc65468ed420e135535261b03845d97b9098f8f08245197c9526d80994f6',
            'ae09010e921de259b02f34ce7fd76f9c09ad224d436fe8fa38aa212177937ffe',
        ]

        xpub_keys = [
            '2df46e04ebf0816e242bfaa1c73e5ebe8863d05d7a96c8aac16f059975e63f30057658de1308930ad4a5663e4f77477014b04954a9d488e62d73b04fc659a35c',
            '7d1de3f22f53904d007ff833fadd7cd6482ea1e83918b985b4ea33e63c16d1837a04a6aab0ed12af562a26db4d10344454274d0bfa6e3581df1dc02f13c5fbe5',
            'f59a28d704df090d8fc641248bdb27d0d001da13ddb332a79cfba8a9fa7233e77f01fc65468ed420e135535261b03845d97b9098f8f08245197c9526d80994f6',
            '723fdc0eb1300fe7f2b9b6989216a831835a88695ba2c2d5c50c8470b7d1b239ae09010e921de259b02f34ce7fd76f9c09ad224d436fe8fa38aa212177937ffe',
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(node, derivation_path)

            self.assertEqual(hexlify(key.node.public_key).decode('utf8'), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code).decode('utf8'), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])
            self.assertEqual(key.root_hd_passphrase, root_hd_passphrase)


if __name__ == '__main__':
    unittest.main()
