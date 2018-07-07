from common import *

from apps.wallet.sign_tx.signing import *
from apps.common import coins
from trezor.crypto import bip32, bip39


class TestAddressGRS(unittest.TestCase):
    # pylint: disable=C0301

    def test_p2pkh_node_derive_address(self):
        coin = coins.by_name('Groestlcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, coin.curve_name)

        node = node_derive(root, [44 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 1, 0])
        address = node.address(coin.address_type) # generate in trezor-crypto
        self.assertEqual(address, 'FmRaqvVBRrAp2Umfqx9V1ectZy8gw54QDN')
        address = address_pkh(node.public_key(), coin) # generate in trezor-core
        self.assertEqual(address, 'FmRaqvVBRrAp2Umfqx9V1ectZy8gw54QDN')

        node = node_derive(root, [44 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 1, 1])
        address = node.address(coin.address_type)
        self.assertEqual(address, 'Fmhtxeh7YdCBkyQF7AQG4QnY8y3rJg89di')
        address = address_pkh(node.public_key(), coin)
        self.assertEqual(address, 'Fmhtxeh7YdCBkyQF7AQG4QnY8y3rJg89di')

        node = node_derive(root, [44 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 0, 0])
        address = node.address(coin.address_type)
        self.assertEqual(address, 'Fj62rBJi8LvbmWu2jzkaUX1NFXLEqDLoZM')
        address = address_pkh(node.public_key(), coin)
        self.assertEqual(address, 'Fj62rBJi8LvbmWu2jzkaUX1NFXLEqDLoZM')

    def test_p2wpkh_in_p2sh_node_derive_address(self):
        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, coin.curve_name)

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)
        self.assertEqual(address, '2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 1])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)
        self.assertEqual(address, '2NFWLCJQBSpz1oUJwwLpX8ECifFWGxQyzGu')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)
        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e')

    def test_p2sh_address(self):
        coin = coins.by_name('Groestlcoin Testnet')

        address = address_p2sh(unhexlify('7a55d61848e77ca266e79a39bfc85c580a6426c9'), coin)
        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e')

    def test_p2wpkh_node_derive_address(self):
        coin = coins.by_name('Groestlcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, coin.curve_name)

        node = node_derive(root, [84 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 1, 0])
        address = address_p2wpkh(node.public_key(), coin.bech32_prefix)
        self.assertEqual(address, 'grs1qzfpwn55tvkxcw0xwfa0g8k2gtlzlgkcq3z000e')

        node = node_derive(root, [84 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 1, 1])
        address = address_p2wpkh(node.public_key(), coin.bech32_prefix)
        self.assertEqual(address, 'grs1qxsgwl66tx7tsuwfm4kk5c5dh6tlfpr4qjqg6gg')

        node = node_derive(root, [84 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 0, 0])
        address = address_p2wpkh(node.public_key(), coin.bech32_prefix)
        self.assertEqual(address, 'grs1qw4teyraux2s77nhjdwh9ar8rl9dt7zww8r6lne')


if __name__ == '__main__':
    unittest.main()
