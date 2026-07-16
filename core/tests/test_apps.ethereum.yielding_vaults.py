# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.ethereum import yielding_vaults


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumYieldingVaults(unittest.TestCase):
    def test_known_vault_addresses(self):
        # Verify that the hardcoded address bytes match the published
        # Etherscan addresses, so a typo in the literals cannot silently
        # route users to a wrong vault.
        self.assertEqual(
            yielding_vaults._TEST_SH_USDC_VAULT_ADDRESS,
            unhexlify("a511d618cd0f9d7cad791009d7c5e3b19c9568da"),
        )
        # https://etherscan.io/address/0xde6c23E561F3e55846207EC45A91b777e0F7C889
        self.assertEqual(
            yielding_vaults._SH_USDC_VAULT_ADDRESS,
            unhexlify("de6c23e561f3e55846207ec45a91b777e0f7c889"),
        )
        # https://etherscan.io/address/0xE4DB1c5A1B709CE4d2adA6985D9D506e58F73829
        self.assertEqual(
            yielding_vaults._SH_USDT_VAULT_ADDRESS,
            unhexlify("e4db1c5a1b709ce4d2ada6985d9d506e58f73829"),
        )
        # https://etherscan.io/address/0x704cFb08969048a8DFf298B214F959791d8Da509
        self.assertEqual(
            yielding_vaults._SH_ETH_VAULT_ADDRESS,
            unhexlify("704cfb08969048a8dff298b214f959791d8da509"),
        )

    def test_known_token_addresses(self):
        # https://etherscan.io/token/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
        self.assertEqual(
            yielding_vaults._USDC_ADDRESS,
            unhexlify("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"),
        )
        # https://etherscan.io/token/0xdAC17F958D2ee523a2206206994597C13D831ec7
        self.assertEqual(
            yielding_vaults._USDT_ADDRESS,
            unhexlify("dac17f958d2ee523a2206206994597c13d831ec7"),
        )
        # https://etherscan.io/token/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
        self.assertEqual(
            yielding_vaults._WETH_ADDRESS,
            unhexlify("c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
        )


if __name__ == "__main__":
    unittest.main()
