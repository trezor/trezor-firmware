from common import *
from ubinascii import unhexlify
from trezor.crypto import nem
from apps.nem.helpers import NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET


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


if __name__ == '__main__':
    unittest.main()
