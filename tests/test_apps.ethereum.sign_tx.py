from common import *
from apps.ethereum import ethereum_sign_tx


class TestEthereumSignTx(unittest.TestCase):

    def test_format(self):
        text = ethereum_sign_tx.format_amount((1).to_bytes(5, 'little'), None, 1)
        self.assertEqual(text, '1 Wei')
        text = ethereum_sign_tx.format_amount((1000).to_bytes(5, 'little'), None, 1)
        self.assertEqual(text, '1000 Wei')

        text = ethereum_sign_tx.format_amount((1000000000000000001).to_bytes(20, 'little'), None, 1)
        self.assertEqual(text, '1 ETH')
        text = ethereum_sign_tx.format_amount((10000000000000000001).to_bytes(20, 'little'), None, 1)
        self.assertEqual(text, '10 ETH')
        text = ethereum_sign_tx.format_amount((10000000000000000001).to_bytes(20, 'little'), None, 61)
        self.assertEqual(text, '10 ETC')
        text = ethereum_sign_tx.format_amount((1000000000000000001).to_bytes(20, 'little'), None, 31)
        self.assertEqual(text, '1 tRSK')

        # unknown chain
        text = ethereum_sign_tx.format_amount((1).to_bytes(20, 'little'), None, 9999)
        self.assertEqual(text, '1 Wei')
        text = ethereum_sign_tx.format_amount((10000000000000000001).to_bytes(20, 'little'), None, 9999)
        self.assertEqual(text, '10 UNKN')


if __name__ == '__main__':
    unittest.main()
