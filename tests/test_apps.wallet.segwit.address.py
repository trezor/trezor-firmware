from common import *

from apps.wallet.sign_tx.signing import *
from apps.common import coins
from trezor.crypto import bip32, bip39


class TestSegwitAddress(unittest.TestCase):
    # pylint: disable=C0301

    def test_p2wpkh_in_p2sh_address(self):

        coin = coins.by_name('Testnet')

        address = get_p2wpkh_in_p2sh_address(
            unhexlify('03a1af804ac108a8a51782198c2d034b28bf90c8803f5a53f76276fa69a4eae77f'),
            coin
        )
        self.assertEqual(address, '2Mww8dCYPUpKHofjgcXcBCEGmniw9CoaiD2')

    def test_p2wpkh_in_p2sh_node_derive_address(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, 'secp256k1')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0])
        address = get_p2wpkh_in_p2sh_address(node.public_key(), coin)

        self.assertEqual(address, '2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 1])
        address = get_p2wpkh_in_p2sh_address(node.public_key(), coin)

        self.assertEqual(address, '2NFWLCJQBSpz1oUJwwLpX8ECifFWGznBVqs')

        node = node_derive(root, [49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0])
        address = get_p2wpkh_in_p2sh_address(node.public_key(), coin)

        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp')


if __name__ == '__main__':
    unittest.main()
