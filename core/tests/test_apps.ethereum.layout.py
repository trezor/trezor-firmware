from common import unittest
from apps.ethereum.layout import format_ethereum_amount


class TestEthereumLayout(unittest.TestCase):

    def test_format(self):
        text = format_ethereum_amount(1, None, 1)
        self.assertEqual(text, '1 Wei ETH')
        text = format_ethereum_amount(1000, None, 1)
        self.assertEqual(text, '1000 Wei ETH')
        text = format_ethereum_amount(1000000, None, 1)
        self.assertEqual(text, '1000000 Wei ETH')
        text = format_ethereum_amount(10000000, None, 1)
        self.assertEqual(text, '10000000 Wei ETH')
        text = format_ethereum_amount(100000000, None, 1)
        self.assertEqual(text, '100000000 Wei ETH')
        text = format_ethereum_amount(1000000000, None, 1)
        self.assertEqual(text, '1000000000 Wei ETH')
        text = format_ethereum_amount(10000000000, None, 1)
        self.assertEqual(text, '0.00000001 ETH')
        text = format_ethereum_amount(100000000000, None, 1)
        self.assertEqual(text, '0.0000001 ETH')
        text = format_ethereum_amount(1000000000000, None, 1)
        self.assertEqual(text, '0.000001 ETH')
        text = format_ethereum_amount(10000000000000, None, 1)
        self.assertEqual(text, '0.00001 ETH')
        text = format_ethereum_amount(100000000000000, None, 1)
        self.assertEqual(text, '0.0001 ETH')
        text = format_ethereum_amount(1000000000000000, None, 1)
        self.assertEqual(text, '0.001 ETH')
        text = format_ethereum_amount(10000000000000000, None, 1)
        self.assertEqual(text, '0.01 ETH')
        text = format_ethereum_amount(100000000000000000, None, 1)
        self.assertEqual(text, '0.1 ETH')
        text = format_ethereum_amount(1000000000000000000, None, 1)
        self.assertEqual(text, '1 ETH')
        text = format_ethereum_amount(10000000000000000000, None, 1)
        self.assertEqual(text, '10 ETH')
        text = format_ethereum_amount(100000000000000000000, None, 1)
        self.assertEqual(text, '100 ETH')
        text = format_ethereum_amount(1000000000000000000000, None, 1)
        self.assertEqual(text, '1000 ETH')

        text = format_ethereum_amount(1000000000000000000, None, 61)
        self.assertEqual(text, '1 ETC')
        text = format_ethereum_amount(1000000000000000000, None, 31)
        self.assertEqual(text, '1 tRBTC')

        text = format_ethereum_amount(1000000000000000001, None, 1)
        self.assertEqual(text, '1.000000000000000001 ETH')
        text = format_ethereum_amount(10000000000000000001, None, 1)
        self.assertEqual(text, '10.000000000000000001 ETH')
        text = format_ethereum_amount(10000000000000000001, None, 61)
        self.assertEqual(text, '10.000000000000000001 ETC')
        text = format_ethereum_amount(1000000000000000001, None, 31)
        self.assertEqual(text, '1.000000000000000001 tRBTC')

        # unknown chain
        text = format_ethereum_amount(1, None, 9999)
        self.assertEqual(text, '1 Wei UNKN')
        text = format_ethereum_amount(10000000000000000001, None, 9999)
        self.assertEqual(text, '10.000000000000000001 UNKN')


if __name__ == '__main__':
    unittest.main()
