from common import *
from ubinascii import unhexlify
from trezor.crypto import nem
from apps.common import HARDENED
from apps.nem.helpers import check_path, NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET


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

    def test_paths(self):
        # 44'/43'/0'/0'/0'
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED]))
        # 44'/43'/0'/0'/0'
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED, 3 | HARDENED, 0 | HARDENED, 0 | HARDENED]))
        # 44'/1'/0'/0'/0'  testnet
        self.assertTrue(check_path([44 | HARDENED, 1 | HARDENED, 3 | HARDENED, 0 | HARDENED, 0 | HARDENED], network=0x98))
        # 44'/43'/0'
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED]))
        # 44'/43'/2'
        self.assertTrue(check_path([44 | HARDENED, 43 | HARDENED, 2 | HARDENED]))
        # 44'/1'/0'  testnet
        self.assertTrue(check_path([44 | HARDENED, 1 | HARDENED, 0 | HARDENED], network=0x98))

        # 44'/43'/0'/0'/1'
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1 | HARDENED]))
        # 44'/43'/0'/1'/1'
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 1 | HARDENED, 1 | HARDENED]))
        # 44'/43'/0'/1'/0'
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 1 | HARDENED, 0 | HARDENED]))
        # 44'/43'/99999'/0'/0'
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 99999000 | HARDENED, 0 | HARDENED, 0 | HARDENED]))
        # 44'/99'/0'/0'/0'
        self.assertFalse(check_path([44 | HARDENED, 99 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED]))
        # 1'/43'/0'/0'/0'
        self.assertFalse(check_path([1 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED]))
        # 44'/43'/0'/0/0
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0, 0]))
        # 44'/43'/0'/0/5
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0 | HARDENED, 0, 5]))
        # 44'/1'/3'/0'/1'  testnet
        self.assertFalse(check_path([44 | HARDENED, 1 | HARDENED, 3 | HARDENED, 0 | HARDENED, 1 | HARDENED], network=0x98))

        # 44'/43'/0/0/1
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0, 0, 1]))
        # 44'/43'/0/0/0
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0, 0, 0]))
        # 44'/43'/0/0'/0'
        self.assertFalse(check_path([44 | HARDENED, 43 | HARDENED, 0, 0 | HARDENED, 0 | HARDENED]))



if __name__ == '__main__':
    unittest.main()
