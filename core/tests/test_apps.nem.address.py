from common import *
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from trezor.crypto import nem
    from apps.nem.helpers import check_path, NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET, NEM_NETWORK_MIJIN


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNemAddress(unittest.TestCase):

    def test_addresses(self):
        pubkey = unhexlify('c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844')
        address = nem.compute_address(pubkey, NEM_NETWORK_MAINNET)
        self.assertEqual(address, 'NDD2CT6LQLIYQ56KIXI3ENTM6EK3D44P5JFXJ4R4')

        pubkey = unhexlify('114171230ad6f8522a000cdc73fbc5c733b30bb71f2b146ccbdf34499f79a810')
        address = nem.compute_address(pubkey, NEM_NETWORK_MAINNET)
        self.assertEqual(address, 'NCUKWDY3J3THKQHAKOK5ALF6ANJQABZHCH7VN6DP')

    def test_validate_address(self):
        validity = nem.validate_address('NDD2CT6LQLIYQ56KIXI3ENTM6EK3D44P5JFXJ4R4', NEM_NETWORK_MAINNET)
        self.assertTrue(validity)

        validity = nem.validate_address('NCUKWDY3J3THKQHAKOK5ALF6ANJQABZHCH7VN6DP', NEM_NETWORK_MAINNET)
        self.assertTrue(validity)

        validity = nem.validate_address('TAU5HO3DRQZNELFEMZZTUKQEZGQ7IUAHKPO7OOLK', NEM_NETWORK_TESTNET)
        self.assertTrue(validity)

        validity = nem.validate_address('nope', NEM_NETWORK_TESTNET)
        self.assertFalse(validity)

        # not valid on testnet
        validity = nem.validate_address('NCUKWDY3J3THKQHAKOK5ALF6ANJQABZHCH7VN6DP', NEM_NETWORK_TESTNET)
        self.assertFalse(validity)

    def test_check_path(self):
        # mainnet path:
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED], NEM_NETWORK_MAINNET))
        # should be valid on mijin as well:
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED], NEM_NETWORK_MIJIN))
        # testnet path:
        self.assertTrue(check_path([44 | HARDENED, 1 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED], NEM_NETWORK_TESTNET))
        # short path (check_path does not validate pattern match):
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED], NEM_NETWORK_MAINNET))

        # testnet path on mainnet:
        self.assertFalse(check_path([44 | HARDENED, 1 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED], NEM_NETWORK_MAINNET))
        # mainnet path on testnet:
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED], NEM_NETWORK_TESTNET))
        # path too short to extract SLIP44:
        self.assertFalse(check_path([44 | HARDENED], NEM_NETWORK_TESTNET))
        # unknown SLIP44:
        self.assertFalse(check_path([44 | HARDENED, 0 | HARDENED], NEM_NETWORK_MAINNET))
        # unhardened SLIP44:
        self.assertFalse(check_path([44 | HARDENED, 43, 0], NEM_NETWORK_MAINNET))


if __name__ == '__main__':
    unittest.main()
