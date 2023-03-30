from common import *
from apps.common.paths import HARDENED

from trezor.crypto.curve import secp256k1

if not utils.BITCOIN_ONLY:
    from apps.binance.helpers import address_from_public_key


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestBinanceAddress(unittest.TestCase):
    def test_privkey_to_address(self):
        #source of test data - binance javascript SDK
        privkey = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"
        expected_address = "tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd"

        pubkey = secp256k1.publickey(unhexlify(privkey), True)
        address = address_from_public_key(pubkey, "tbnb")

        self.assertEqual(address, expected_address)


if __name__ == '__main__':
    unittest.main()
