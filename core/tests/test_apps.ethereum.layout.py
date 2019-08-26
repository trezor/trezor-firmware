from common import *

if not utils.BITCOIN_ONLY:
    from apps.ethereum.layout import format_ethereum_amount
    from apps.ethereum.tokens import token_by_chain_address


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
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
        self.assertEqual(text, '0.000000001 ETH')
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

        # tokens with low decimal values
        # USDC has 6 decimals
        usdc_token = token_by_chain_address(1, unhexlify("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"))
        # ICO has 10 decimals
        ico_token = token_by_chain_address(1, unhexlify("a33e729bf4fdeb868b534e1f20523463d9c46bee"))

        # when decimals < 10, should never display 'Wei' format
        text = format_ethereum_amount(1, usdc_token, 1)
        self.assertEqual(text, '0.000001 USDC')
        text = format_ethereum_amount(0, usdc_token, 1)
        self.assertEqual(text, '0 USDC')

        text = format_ethereum_amount(1, ico_token, 1)
        self.assertEqual(text, '1 Wei ICO')
        text = format_ethereum_amount(9, ico_token, 1)
        self.assertEqual(text, '9 Wei ICO')
        text = format_ethereum_amount(10, ico_token, 1)
        self.assertEqual(text, '0.000000001 ICO')
        text = format_ethereum_amount(11, ico_token, 1)
        self.assertEqual(text, '0.0000000011 ICO')


if __name__ == '__main__':
    unittest.main()
