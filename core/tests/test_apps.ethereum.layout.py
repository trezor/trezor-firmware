# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from ethereum_common import make_network, make_token

    from apps.ethereum import networks
    from apps.ethereum.helpers import format_ethereum_amount
    from apps.ethereum.tokens import UNKNOWN_TOKEN

    ETH = networks.by_chain_id(1)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestFormatEthereumAmount(unittest.TestCase):
    def test_denominations(self):
        text = format_ethereum_amount(1, None, ETH)
        self.assertEqual(text, "1 Wei ETH")
        text = format_ethereum_amount(1000, None, ETH)
        self.assertEqual(text, "1,000 Wei ETH")
        text = format_ethereum_amount(1000000, None, ETH)
        self.assertEqual(text, "1,000,000 Wei ETH")
        text = format_ethereum_amount(10000000, None, ETH)
        self.assertEqual(text, "10,000,000 Wei ETH")
        text = format_ethereum_amount(100000000, None, ETH)
        self.assertEqual(text, "100,000,000 Wei ETH")
        text = format_ethereum_amount(1000000000, None, ETH)
        self.assertEqual(text, "0.000000001 ETH")
        text = format_ethereum_amount(10000000000, None, ETH)
        self.assertEqual(text, "0.00000001 ETH")
        text = format_ethereum_amount(100000000000, None, ETH)
        self.assertEqual(text, "0.0000001 ETH")
        text = format_ethereum_amount(1000000000000, None, ETH)
        self.assertEqual(text, "0.000001 ETH")
        text = format_ethereum_amount(10000000000000, None, ETH)
        self.assertEqual(text, "0.00001 ETH")
        text = format_ethereum_amount(100000000000000, None, ETH)
        self.assertEqual(text, "0.0001 ETH")
        text = format_ethereum_amount(1000000000000000, None, ETH)
        self.assertEqual(text, "0.001 ETH")
        text = format_ethereum_amount(10000000000000000, None, ETH)
        self.assertEqual(text, "0.01 ETH")
        text = format_ethereum_amount(100000000000000000, None, ETH)
        self.assertEqual(text, "0.1 ETH")
        text = format_ethereum_amount(1000000000000000000, None, ETH)
        self.assertEqual(text, "1 ETH")
        text = format_ethereum_amount(10000000000000000000, None, ETH)
        self.assertEqual(text, "10 ETH")
        text = format_ethereum_amount(100000000000000000000, None, ETH)
        self.assertEqual(text, "100 ETH")
        text = format_ethereum_amount(1000000000000000000000, None, ETH)
        self.assertEqual(text, "1,000 ETH")

    def test_force_units(self):
        wei_amount = 100_000_000
        text = format_ethereum_amount(wei_amount, None, ETH)
        self.assertEqual(text, "100,000,000 Wei ETH")
        text = format_ethereum_amount(wei_amount, None, ETH, force_unit_gwei=True)
        self.assertEqual(text, "0.1 Gwei")

    def test_precision(self):
        text = format_ethereum_amount(1000000000000000001, None, ETH)
        self.assertEqual(text, "1.000000000000000001 ETH")
        text = format_ethereum_amount(10000000000000000001, None, ETH)
        self.assertEqual(text, "10.000000000000000001 ETH")

    def test_symbols(self):
        fake_network = make_network(symbol="FAKE")
        text = format_ethereum_amount(1, None, fake_network)
        self.assertEqual(text, "1 Wei FAKE")
        text = format_ethereum_amount(1000000000000000000, None, fake_network)
        self.assertEqual(text, "1 FAKE")
        text = format_ethereum_amount(1000000000000000001, None, fake_network)
        self.assertEqual(text, "1.000000000000000001 FAKE")

    def test_unknown_chain(self):
        # unknown chain
        text = format_ethereum_amount(1, None, networks.UNKNOWN_NETWORK)
        self.assertEqual(text, "1 Wei UNKN")
        text = format_ethereum_amount(
            10000000000000000001, None, networks.UNKNOWN_NETWORK
        )
        self.assertEqual(text, "10.000000000000000001 UNKN")

    def test_tokens(self):
        # tokens with low decimal values
        # USDC has 6 decimals
        usdc_token = make_token(symbol="USDC", decimals=6)
        # when decimals < 10, should never display 'Wei' format
        text = format_ethereum_amount(1, usdc_token, ETH)
        self.assertEqual(text, "0.000001 USDC")
        text = format_ethereum_amount(0, usdc_token, ETH)
        self.assertEqual(text, "0 USDC")

        # ICO has 10 decimals
        ico_token = make_token(symbol="ICO", decimals=10)
        text = format_ethereum_amount(1, ico_token, ETH)
        self.assertEqual(text, "1 Wei ICO")
        text = format_ethereum_amount(9, ico_token, ETH)
        self.assertEqual(text, "9 Wei ICO")
        text = format_ethereum_amount(10, ico_token, ETH)
        self.assertEqual(text, "0.000000001 ICO")
        text = format_ethereum_amount(11, ico_token, ETH)
        self.assertEqual(text, "0.0000000011 ICO")

    def test_unknown_token(self):
        text = format_ethereum_amount(1, UNKNOWN_TOKEN, ETH)
        self.assertEqual(text, "1 Wei UNKN")
        text = format_ethereum_amount(0, UNKNOWN_TOKEN, ETH)
        self.assertEqual(text, "0 Wei UNKN")
        # unknown token has 0 decimals so is always wei
        text = format_ethereum_amount(1000000000000000000, UNKNOWN_TOKEN, ETH)
        self.assertEqual(text, "1,000,000,000,000,000,000 Wei UNKN")


if __name__ == "__main__":
    unittest.main()
