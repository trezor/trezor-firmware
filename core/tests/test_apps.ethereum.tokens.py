# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.ethereum import tokens


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumTokens(unittest.TestCase):
    def test_token_by_chain_address(self):

        token = tokens.token_by_chain_address(
            1,
            b"\x7f\xc6\x65\x00\xc8\x4a\x76\xad\x7e\x9c\x93\x43\x7b\xfc\x5a\xc3\x3e\x2d\xda\xe9",
        )
        self.assertEqual(token.symbol, "AAVE")

        # invalid adress, invalid chain
        token = tokens.token_by_chain_address(999, b"\x00\xFF")
        self.assertIs(token, None)

        self.assertEqual(tokens.UNKNOWN_TOKEN.symbol, "Wei UNKN")
        self.assertEqual(tokens.UNKNOWN_TOKEN.decimals, 0)


if __name__ == "__main__":
    unittest.main()
