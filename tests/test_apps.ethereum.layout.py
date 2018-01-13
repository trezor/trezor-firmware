from common import *
from apps.ethereum.layout import format_amount


class TestEthereumLayout(unittest.TestCase):

    def test_format(self):
        text = format_amount((1).to_bytes(5, 'big'), None, 1)
        self.assertEqual(text, '1 Wei')
        text = format_amount((1000).to_bytes(5, 'big'), None, 1)
        self.assertEqual(text, '1000 Wei')

        text = format_amount((1000000000000000001).to_bytes(20, 'big'), None, 1)
        self.assertEqual(text, '1 ETH')
        text = format_amount((10000000000000000001).to_bytes(20, 'big'), None, 1)
        self.assertEqual(text, '10 ETH')
        text = format_amount((10000000000000000001).to_bytes(20, 'big'), None, 61)
        self.assertEqual(text, '10 ETC')
        text = format_amount((1000000000000000001).to_bytes(20, 'big'), None, 31)
        self.assertEqual(text, '1 tRSK')

        # unknown chain
        text = format_amount((1).to_bytes(20, 'big'), None, 9999)
        self.assertEqual(text, '1 Wei')
        text = format_amount((10000000000000000001).to_bytes(20, 'big'), None, 9999)
        self.assertEqual(text, '10 UNKN')


if __name__ == '__main__':
    unittest.main()
