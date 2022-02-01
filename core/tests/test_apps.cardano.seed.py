from common import *
from trezor.crypto import cardano

from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.cardano.seed import Keychain
    from apps.cardano.get_public_key import _get_public_key


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoKeychain(unittest.TestCase):
    def test_various_paths_at_once(self):
        mnemonic = (
            "test walk nut penalty hip pave soap entry language right filter choice"
        )
        passphrase = ""
        secret = cardano.derive_icarus(mnemonic, passphrase, True)
        node = cardano.from_secret(secret)
        keychain = Keychain(node)

        derivation_paths = [
            [44 | HARDENED, 1815 | HARDENED, HARDENED, 0, 0],
            [44 | HARDENED, 1815 | HARDENED, HARDENED, 0, 1],
            [1852 | HARDENED, 1815 | HARDENED, HARDENED, 0, 0],
            [1852 | HARDENED, 1815 | HARDENED, HARDENED, 0, 1],
            [44 | HARDENED, 1815 | HARDENED, HARDENED, 0, 2],
            [1852 | HARDENED, 1815 | HARDENED, HARDENED, 0, 2],
        ]

        public_keys = [
            b"badd2852ccda7492364be0f88f2ba0b78c5f2d7179a941f1d19f756112b66afa",
            b"34377409140c061d76778626d43456880d5471c1cbade8c372cb6a3be9678072",
            b"73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d",
            b"f626ab887eb5f40b502463ccf2ec5a7311676ee9e5d55c492059a366c0b4d4a1",
            b"408ee7b2d1c84d7899dba07150fae88c5411974f1762cb659dd928db8aac206b",
            b"86e8a3880767e1ed521a47de1e031d47f33d5a8095be467bffbbd3295e27258e",
        ]

        chain_codes = [
            b"e1c5d15875d3ed68667978af38fe3fe586511d87a784c0962a333c21e63a865d",
            b"15c987276326a82defa4cb6762d43442f09e5dcbcc37fa0c58f24ae2dba3d3eb",
            b"dd75e154da417becec55cdd249327454138f082110297d5e87ab25e15fad150f",
            b"f7ab126f2884db9059fa09ca83be6b8bd0250426aeb62191bdd9861457b8bc91",
            b"18d5c9d20c8d23bed068c9ff3a1126b940f0e537f9d94891828a999dda6fafd1",
            b"580bba4bb0b9c56974e16a6998322a91e857e2fac28674404da993f6197fd29f",
        ]

        xpub_keys = [
            "badd2852ccda7492364be0f88f2ba0b78c5f2d7179a941f1d19f756112b66afae1c5d15875d3ed68667978af38fe3fe586511d87a784c0962a333c21e63a865d",
            "34377409140c061d76778626d43456880d5471c1cbade8c372cb6a3be967807215c987276326a82defa4cb6762d43442f09e5dcbcc37fa0c58f24ae2dba3d3eb",
            "73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7ddd75e154da417becec55cdd249327454138f082110297d5e87ab25e15fad150f",
            "f626ab887eb5f40b502463ccf2ec5a7311676ee9e5d55c492059a366c0b4d4a1f7ab126f2884db9059fa09ca83be6b8bd0250426aeb62191bdd9861457b8bc91",
            "408ee7b2d1c84d7899dba07150fae88c5411974f1762cb659dd928db8aac206b18d5c9d20c8d23bed068c9ff3a1126b940f0e537f9d94891828a999dda6fafd1",
            "86e8a3880767e1ed521a47de1e031d47f33d5a8095be467bffbbd3295e27258e580bba4bb0b9c56974e16a6998322a91e857e2fac28674404da993f6197fd29f",
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(keychain, derivation_path)

            self.assertEqual(hexlify(key.node.public_key), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoDerivation(unittest.TestCase):
    def test_icarus(self):
        # vectors from:
        # https://github.com/cardano-foundation/CIPs/blob/master/CIP-0003/Icarus.md
        mnemonic = "eight country switch draw meat scout mystery blade tip drift useless good keep usage title"

        secret = cardano.derive_icarus(mnemonic, "", False)
        self.assertEqual(
            hexlify(secret).decode(),
            "c065afd2832cd8b087c4d9ab7011f481ee1e0721e78ea5dd609f3ab3f156d245"
            "d176bd8fd4ec60b4731c3918a2a72a0226c0cd119ec35b47e4d55884667f552a"
            "23f7fdcd4a10c6cd2c7393ac61d877873e248f417634aa3d812af327ffe9d620",
        )
        secret_trezor = cardano.derive_icarus(mnemonic, "", True)
        self.assertEqual(secret, secret_trezor)

        secret = cardano.derive_icarus(mnemonic, "foo", False)
        self.assertEqual(
            hexlify(secret).decode(),
            "70531039904019351e1afb361cd1b312a4d0565d4ff9f8062d38acf4b15cce41"
            "d7b5738d9c893feea55512a3004acb0d222c35d3e3d5cde943a15a9824cbac59"
            "443cf67e589614076ba01e354b1a432e0e6db3b59e37fc56b5fb0222970a010e",
        )
        secret_trezor = cardano.derive_icarus(mnemonic, "foo", True)
        self.assertEqual(secret, secret_trezor)

    def test_icarus_trezor(self):
        mnemonic = (
            "void come effort suffer camp survey warrior heavy "
            "shoot primary clutch crush open amazing screen patrol "
            "group space point ten exist slush involve unfold"
        )
        secret = cardano.derive_icarus(mnemonic, "", True)
        self.assertEqual(
            hexlify(secret).decode(),
            "409bb7a2998ec48029c8d2956fabd043a368ccc9b5120e42dd8a5c7145d08f45"
            "e8e8664d06f62b4fc3bab0134778af27ddf059a4ad1eb0efefeedd8189bbfe00"
            "deb289c5cdc2cf8ccfa19aea63b28424a4b0045b4b762292d46b73aa1c5cc99a",
        )
        secret_icarus = cardano.derive_icarus(mnemonic, "", False)
        self.assertNotEqual(secret, secret_icarus)

        PASSPHRASE = "foo"
        secret = cardano.derive_icarus(mnemonic, PASSPHRASE, True)
        self.assertEqual(
            hexlify(secret).decode(),
            "c8ab7a160a66bfa7a118f553c4eebfe7444e36e449dac7d6eeae21f3bbaa9551"
            "8593025160068776a4d61c0efc4f698585bb59f1aebe93c58e1eaf557ab59502"
            "d9f68fbea3049bc2255d15fc63803e9c3dbb78abff2d53f8356794807d402568",
        )
        secret_icarus = cardano.derive_icarus(mnemonic, PASSPHRASE, False)
        self.assertNotEqual(secret, secret_icarus)


if __name__ == "__main__":
    unittest.main()
