from common import *

from apps.wallet.sign_tx.signing import *
from apps.common import coins
from trezor.crypto import bip32, bip39


class TestAddress(unittest.TestCase):
    # pylint: disable=C0301

    def test_p2wpkh_in_p2sh_address(self):
        coin = coins.by_name('Testnet')
        address = address_p2wpkh_in_p2sh(
            unhexlify('03a1af804ac108a8a51782198c2d034b28bf90c8803f5a53f76276fa69a4eae77f'),
            coin.address_type_p2sh
        )
        self.assertEqual(address, '2Mww8dCYPUpKHofjgcXcBCEGmniw9CoaiD2')

    def test_p2wpkh_in_p2sh_script_address(self):
        raw = address_p2wpkh_in_p2sh_script(
            unhexlify('03a1af804ac108a8a51782198c2d034b28bf90c8803f5a53f76276fa69a4eae77f')
        )
        self.assertEqual(raw, unhexlify('336caa13e08b96080a32b5d818d59b4ab3b36742'))

    def test_p2wpkh_in_p2sh_node_derive_address(self):
        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, 'secp256k1')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin.address_type_p2sh)

        self.assertEqual(address, '2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 1])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin.address_type_p2sh)

        self.assertEqual(address, '2NFWLCJQBSpz1oUJwwLpX8ECifFWGznBVqs')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin.address_type_p2sh)

        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp')

    def test_p2wpkh_address(self):
        # data from https://bc-2.jp/tools/bech32demo/index.html
        coin = coins.by_name('Testnet')
        address = address_p2wpkh(
            unhexlify('0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'),
            coin.bech32_prefix
        )
        self.assertEqual(address, 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx')

    def test_p2sh_address(self):
        coin = coins.by_name('Testnet')

        address = address_p2sh(
            unhexlify('7a55d61848e77ca266e79a39bfc85c580a6426c9'),
            coin.address_type_p2sh
        )
        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp')

    def test_p2wsh_address(self):
        coin = coins.by_name('Testnet')

        # pubkey OP_CHECKSIG
        script = unhexlify('210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac')
        h = HashWriter(sha256)
        write_bytes(h, script)

        address = address_p2wsh(
            h.get_digest(),
            coin.bech32_prefix
        )
        self.assertEqual(address, 'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7')

    def test_p2wsh_in_p2sh_address(self):
        coin = coins.by_name('Bitcoin')

        # data from Mastering Bitcoin
        address = address_p2wsh_in_p2sh(
            unhexlify('9592d601848d04b172905e0ddb0adde59f1590f1e553ffc81ddc4b0ed927dd73'),
            coin.address_type_p2sh
        )
        self.assertEqual(address, '3Dwz1MXhM6EfFoJChHCxh1jWHb8GQqRenG')

    def test_p2wsh_in_p2sh_script_address(self):
        raw = address_p2wsh_in_p2sh_script(
            unhexlify('1863143c14c5166804bd19203356da136c985678cd4d27a1b8c6329604903262')
        )
        self.assertEqual(raw, unhexlify('e4300531190587e3880d4c3004f5355d88ff928d'))


if __name__ == '__main__':
    unittest.main()
