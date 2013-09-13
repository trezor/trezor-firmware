import unittest
import common

class TestAddresses(common.TrezorTest):
    def test_btc(self):
        self.client.load_device(seed=self.mnemonic1, pin='')
        self.client.apply_settings(coin_shortcut='BTC')

        self.assertEqual(self.client.get_address([]), '1GBDQapuquKZGPxWTB39s5bayLDTv5sD77')
        self.assertEqual(self.client.get_address([1]), '13HWRT9JtftSF6uv65eMrQowHn3CioKegP')
        self.assertEqual(self.client.get_address([0, 1]), '1GnnT11aZeH6QZCtT7EjCvRF3EXHoY3owE')
        self.assertEqual(self.client.get_address([9, 0]), '1KeRRK74ARTxnby8dYsm2UreAx5tBGbbY7')
        self.assertEqual(self.client.get_address([0, 9999999]), '1JeDAdRMxeuWCQ8ohWySCD5KEPoN2sEanK')

    def test_ltc(self):
        self.client.load_device(seed=self.mnemonic1, pin='')
        self.client.apply_settings(coin_shortcut='LTC')

        self.assertEqual(self.client.get_address([]), 'LaQAfo8jvZZcXCefdK2T96fMBYak5XomhR')
        self.assertEqual(self.client.get_address([1]), 'LMWTgfT8yL8VVuc5GDdf8RshVzQUw9AoUK')
        self.assertEqual(self.client.get_address([0, 1]), 'Lb1jiDKQeJX9fMu3dFE2UwV1FStZwvijfE')
        self.assertEqual(self.client.get_address([9, 0]), 'LdsNgXQtF5i23QfHogs4JVvQPATAFbfWYA')
        self.assertEqual(self.client.get_address([0, 9999999]), 'LcsARqjC3K9ZTCpxsexjUE95ScAeEPqR69')

    def test_tbtc(self):
        self.client.load_device(seed=self.mnemonic1, pin='')
        self.client.apply_settings(coin_shortcut='tBTC')

        self.assertEqual(self.client.get_address([111, 42]), 'mypL2oDrCj4196uuvtC6QJnsetu3YMUdB7')
 
if __name__ == '__main__':
    unittest.main()        
