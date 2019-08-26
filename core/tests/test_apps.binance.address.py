from common import *
from apps.common.paths import HARDENED

from trezor.crypto.curve import secp256k1

if not utils.BITCOIN_ONLY:
    from apps.binance.helpers import address_from_public_key, validate_full_path


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestBinanceAddress(unittest.TestCase):
    def test_privkey_to_address(self):
        #source of test data - binance javascript SDK
        privkey = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"
        expected_address = "tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd"

        pubkey = secp256k1.publickey(unhexlify(privkey), True)
        address = address_from_public_key(pubkey, "tbnb")

        self.assertEqual(address, expected_address)


    def test_paths(self):
    # 44'/714'/a'/0/0 is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 714 | HARDENED],
            [44 | HARDENED, 714 | HARDENED, 0],
            [44 | HARDENED, 714 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 714 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 714 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 714 | HARDENED, 0 | HARDENED, 0, 5],
            [44 | HARDENED, 714 | HARDENED, 9999 | HARDENED],
            [44 | HARDENED, 714 | HARDENED, 9999000 | HARDENED, 0, 0],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0],
            [1 | HARDENED, 1 | HARDENED, 1 | HARDENED],
        ]
        correct_paths = [
            [44 | HARDENED, 714 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 714 | HARDENED, 3 | HARDENED, 0, 0],
            [44 | HARDENED, 714 | HARDENED, 9 | HARDENED, 0, 0],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == '__main__':
    unittest.main()
