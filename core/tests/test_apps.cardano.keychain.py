from common import *
from trezor import wire
from trezor.crypto import bip32, slip39

from apps.common import HARDENED, seed

if not utils.BITCOIN_ONLY:
    from apps.cardano.seed import Keychain
    from apps.cardano.get_public_key import _get_public_key


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoKeychain(unittest.TestCase):
    def test_various_paths_at_once(self):
        mnemonic = "test walk nut penalty hip pave soap entry language right filter choice"
        passphrase = ""
        node = bip32.from_mnemonic_cardano(mnemonic, passphrase)
        keychain = Keychain(node)

        derivation_paths = [
            [44 | HARDENED, 1815 | HARDENED, HARDENED, 0, 0],
            [44 | HARDENED, 1815 | HARDENED, HARDENED, 0, 1],
            [1852 | HARDENED, 1815 | HARDENED, HARDENED, 0, 0],
            [1852 | HARDENED, 1815 | HARDENED, HARDENED, 0, 1],
            [44 | HARDENED, 1815 | HARDENED, HARDENED, 0, 2],
            [1852 | HARDENED, 1815 | HARDENED, HARDENED, 0, 2]
        ]

        public_keys = [
            b'badd2852ccda7492364be0f88f2ba0b78c5f2d7179a941f1d19f756112b66afa',
            b'34377409140c061d76778626d43456880d5471c1cbade8c372cb6a3be9678072',
            b'73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d',
            b'f626ab887eb5f40b502463ccf2ec5a7311676ee9e5d55c492059a366c0b4d4a1',
            b'408ee7b2d1c84d7899dba07150fae88c5411974f1762cb659dd928db8aac206b',
            b'86e8a3880767e1ed521a47de1e031d47f33d5a8095be467bffbbd3295e27258e'
        ]

        chain_codes = [
            b"e1c5d15875d3ed68667978af38fe3fe586511d87a784c0962a333c21e63a865d",
            b"15c987276326a82defa4cb6762d43442f09e5dcbcc37fa0c58f24ae2dba3d3eb",
            b"dd75e154da417becec55cdd249327454138f082110297d5e87ab25e15fad150f",
            b"f7ab126f2884db9059fa09ca83be6b8bd0250426aeb62191bdd9861457b8bc91",
            b"18d5c9d20c8d23bed068c9ff3a1126b940f0e537f9d94891828a999dda6fafd1",
            b"580bba4bb0b9c56974e16a6998322a91e857e2fac28674404da993f6197fd29f"
        ]

        xpub_keys = [
            "badd2852ccda7492364be0f88f2ba0b78c5f2d7179a941f1d19f756112b66afae1c5d15875d3ed68667978af38fe3fe586511d87a784c0962a333c21e63a865d",
            "34377409140c061d76778626d43456880d5471c1cbade8c372cb6a3be967807215c987276326a82defa4cb6762d43442f09e5dcbcc37fa0c58f24ae2dba3d3eb",
            "73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7ddd75e154da417becec55cdd249327454138f082110297d5e87ab25e15fad150f",
            "f626ab887eb5f40b502463ccf2ec5a7311676ee9e5d55c492059a366c0b4d4a1f7ab126f2884db9059fa09ca83be6b8bd0250426aeb62191bdd9861457b8bc91",
            "408ee7b2d1c84d7899dba07150fae88c5411974f1762cb659dd928db8aac206b18d5c9d20c8d23bed068c9ff3a1126b940f0e537f9d94891828a999dda6fafd1",
            "86e8a3880767e1ed521a47de1e031d47f33d5a8095be467bffbbd3295e27258e580bba4bb0b9c56974e16a6998322a91e857e2fac28674404da993f6197fd29f"
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(keychain, derivation_path)

            self.assertEqual(hexlify(key.node.public_key), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])


if __name__ == '__main__':
    unittest.main()
