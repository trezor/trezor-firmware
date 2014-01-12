import unittest
import common

class TestAddresses(common.TrezorTest):
    def test_btc(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin='',
                                            passphrase_protection=False,
                                            label='test',
                                            language='english')

        self.assertEqual(self.client.get_address('Bitcoin', []), '1EfKbQupktEMXf4gujJ9kCFo83k1iMqwqK')
        self.assertEqual(self.client.get_address('Bitcoin', [1]), '1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb')
        self.assertEqual(self.client.get_address('Bitcoin', [0, -1]), '1JVq66pzRBvqaBRFeU9SPVvg3er4ZDgoMs')
        self.assertEqual(self.client.get_address('Bitcoin', [-9, 0]), '1F4YdQdL9ZQwvcNTuy5mjyQxXkyCfMcP2P')
        self.assertEqual(self.client.get_address('Bitcoin', [0, 9999999]), '1GS8X3yc7ntzwGw9vXwj9wqmBWZkTFewBV')

    def test_ltc(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin='',
                                            passphrase_protection=False,
                                            label='test',
                                            language='english')

        self.assertEqual(self.client.get_address('Litecoin', []), 'LYtGrdDeqYUQnTkr5sHT2DKZLG7Hqg7HTK')
        self.assertEqual(self.client.get_address('Litecoin', [1]), 'LKRGNecThFP3Q6c5fosLVA53Z2hUDb1qnE')
        self.assertEqual(self.client.get_address('Litecoin', [0, -1]), 'LcinMK8pVrAtpz7Qpc8jfWzSFsDLgLYfG6')
        self.assertEqual(self.client.get_address('Litecoin', [-9, 0]), 'LZHVtcwAEDf1BR4d67551zUijyLUpDF9EX')
        self.assertEqual(self.client.get_address('Litecoin', [0, 9999999]), 'Laf5nGHSCT94C5dK6fw2RxuXPiw2ZuRR9S')

    def test_tbtc(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin='',
                                            passphrase_protection=False,
                                            label='test',
                                            language='english')

        self.assertEqual(self.client.get_address('Testnet', [111, 42]), 'moN6aN6NP1KWgnPSqzrrRPvx2x1UtZJssa')
 
if __name__ == '__main__':
    unittest.main()        
