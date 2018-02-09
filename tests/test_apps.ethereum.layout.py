from common import *
from apps.ethereum.layout import format_ethereum_amount


class TestEthereumLayout(unittest.TestCase):

    def test_format(self):
        text = format_ethereum_amount((1).to_bytes(5, 'big'), None, 1)
        self.assertEqual(text, '1 Wei')
        text = format_ethereum_amount((1000).to_bytes(5, 'big'), None, 1)
        self.assertEqual(text, '1000 Wei')

        text = format_ethereum_amount((1000000000000000000).to_bytes(20, 'big'), None, 1)
        self.assertEqual(text, '1 ETH')
        text = format_ethereum_amount((10000000000000000000).to_bytes(20, 'big'), None, 1)
        self.assertEqual(text, '10 ETH')
        text = format_ethereum_amount((10000000000000000000).to_bytes(20, 'big'), None, 61)
        self.assertEqual(text, '10 ETC')
        text = format_ethereum_amount((1000000000000000000).to_bytes(20, 'big'), None, 31)
        self.assertEqual(text, '1 tRSK')

        text = format_ethereum_amount((1000000000000000001).to_bytes(20, 'big'), None, 1)
        self.assertEqual(text, '1.000000000000000001 ETH')
        text = format_ethereum_amount((10000000000000000001).to_bytes(20, 'big'), None, 1)
        self.assertEqual(text, '10.000000000000000001 ETH')
        text = format_ethereum_amount((10000000000000000001).to_bytes(20, 'big'), None, 61)
        self.assertEqual(text, '10.000000000000000001 ETC')
        text = format_ethereum_amount((1000000000000000001).to_bytes(20, 'big'), None, 31)
        self.assertEqual(text, '1.000000000000000001 tRSK')

        # unknown chain
        text = format_ethereum_amount((1).to_bytes(20, 'big'), None, 9999)
        self.assertEqual(text, '1 Wei')
        text = format_ethereum_amount((10000000000000000001).to_bytes(20, 'big'), None, 9999)
        self.assertEqual(text, '10.000000000000000001 UNKN')


if __name__ == '__main__':
    unittest.main()
