from common import *

if not utils.BITCOIN_ONLY:
    from apps.ethereum.layout import format_ethereum_amount
    from apps.ethereum.tokens import token_by_chain_address
    from ethereum_common import construct_network_info, construct_token_info


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestFormatEthereumAmount(unittest.TestCase):

    def setUp(self):
        self.eth_network = construct_network_info(shortcut="ETH")

    def test_format(self):
        text = format_ethereum_amount(1, None, self.eth_network)
        self.assertEqual(text, '1 Wei ETH')
        text = format_ethereum_amount(1000, None, self.eth_network)
        self.assertEqual(text, '1,000 Wei ETH')
        text = format_ethereum_amount(1000000, None, self.eth_network)
        self.assertEqual(text, '1,000,000 Wei ETH')
        text = format_ethereum_amount(10000000, None, self.eth_network)
        self.assertEqual(text, '10,000,000 Wei ETH')
        text = format_ethereum_amount(100000000, None, self.eth_network)
        self.assertEqual(text, '100,000,000 Wei ETH')
        text = format_ethereum_amount(1000000000, None, self.eth_network)
        self.assertEqual(text, '0.000000001 ETH')
        text = format_ethereum_amount(10000000000, None, self.eth_network)
        self.assertEqual(text, '0.00000001 ETH')
        text = format_ethereum_amount(100000000000, None, self.eth_network)
        self.assertEqual(text, '0.0000001 ETH')
        text = format_ethereum_amount(1000000000000, None, self.eth_network)
        self.assertEqual(text, '0.000001 ETH')
        text = format_ethereum_amount(10000000000000, None, self.eth_network)
        self.assertEqual(text, '0.00001 ETH')
        text = format_ethereum_amount(100000000000000, None, self.eth_network)
        self.assertEqual(text, '0.0001 ETH')
        text = format_ethereum_amount(1000000000000000, None, self.eth_network)
        self.assertEqual(text, '0.001 ETH')
        text = format_ethereum_amount(10000000000000000, None, self.eth_network)
        self.assertEqual(text, '0.01 ETH')
        text = format_ethereum_amount(100000000000000000, None, self.eth_network)
        self.assertEqual(text, '0.1 ETH')
        text = format_ethereum_amount(1000000000000000000, None, self.eth_network)
        self.assertEqual(text, '1 ETH')
        text = format_ethereum_amount(10000000000000000000, None, self.eth_network)
        self.assertEqual(text, '10 ETH')
        text = format_ethereum_amount(100000000000000000000, None, self.eth_network)
        self.assertEqual(text, '100 ETH')
        text = format_ethereum_amount(1000000000000000000000, None, self.eth_network)
        self.assertEqual(text, '1,000 ETH')

        text = format_ethereum_amount(1000000000000000000, None, construct_network_info(shortcut="ETC"))
        self.assertEqual(text, '1 ETC')
        text = format_ethereum_amount(1000000000000000000, None, construct_network_info(shortcut="tRBTC"))
        self.assertEqual(text, '1 tRBTC')

        text = format_ethereum_amount(1000000000000000001, None, self.eth_network)
        self.assertEqual(text, '1.000000000000000001 ETH')
        text = format_ethereum_amount(10000000000000000001, None, self.eth_network)
        self.assertEqual(text, '10.000000000000000001 ETH')
        text = format_ethereum_amount(10000000000000000001, None, construct_network_info(shortcut="ETC"))
        self.assertEqual(text, '10.000000000000000001 ETC')
        text = format_ethereum_amount(1000000000000000001, None, construct_network_info(shortcut="tRBTC"))
        self.assertEqual(text, '1.000000000000000001 tRBTC')

    def test_unknown_chain(self):
        # unknown chain
        text = format_ethereum_amount(1, None, None)
        self.assertEqual(text, '1 Wei UNKN')
        text = format_ethereum_amount(10000000000000000001, None, None)
        self.assertEqual(text, '10.000000000000000001 UNKN')

    def test_tokens(self):
        # tokens with low decimal values
        # USDC has 6 decimals
        usdc_token = construct_token_info(symbol="USDC", decimals=6)
        # ICO has 10 decimals
        ico_token = construct_token_info(symbol="ICO", decimals=10)

        # when decimals < 10, should never display 'Wei' format
        text = format_ethereum_amount(1, usdc_token, self.eth_network)
        self.assertEqual(text, '0.000001 USDC')
        text = format_ethereum_amount(0, usdc_token, self.eth_network)
        self.assertEqual(text, '0 USDC')

        text = format_ethereum_amount(1, ico_token, self.eth_network)
        self.assertEqual(text, '1 Wei ICO')
        text = format_ethereum_amount(9, ico_token, self.eth_network)
        self.assertEqual(text, '9 Wei ICO')
        text = format_ethereum_amount(10, ico_token, self.eth_network)
        self.assertEqual(text, '0.000000001 ICO')
        text = format_ethereum_amount(11, ico_token, self.eth_network)
        self.assertEqual(text, '0.0000000011 ICO')

    def test_unknown_token(self):
        unknown_token = token_by_chain_address(1, b"hello")
        text = format_ethereum_amount(1, unknown_token, self.eth_network)
        self.assertEqual(text, '1 Wei UNKN')
        text = format_ethereum_amount(0, unknown_token, self.eth_network)
        self.assertEqual(text, '0 Wei UNKN')
        # unknown token has 0 decimals so is always wei
        text = format_ethereum_amount(1000000000000000000, unknown_token, self.eth_network)
        self.assertEqual(text, '1,000,000,000,000,000,000 Wei UNKN')


if __name__ == '__main__':
    unittest.main()
