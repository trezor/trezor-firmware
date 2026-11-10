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
            bytes.fromhex("a511d618cd0f9d7cad791009d7c5e3b19c9568da"),
        )
        # https://etherscan.io/address/0xde6c23E561F3e55846207EC45A91b777e0F7C889
        self.assertEqual(
            yielding_vaults._SH_USDC_VAULT_ADDRESS,
            bytes.fromhex("de6c23e561f3e55846207ec45a91b777e0f7c889"),
        )
        # https://etherscan.io/address/0xE4DB1c5A1B709CE4d2adA6985D9D506e58F73829
        self.assertEqual(
            yielding_vaults._SH_USDT_VAULT_ADDRESS,
            bytes.fromhex("e4db1c5a1b709ce4d2ada6985d9d506e58f73829"),
        )
        # https://etherscan.io/address/0x704cFb08969048a8DFf298B214F959791d8Da509
        self.assertEqual(
            yielding_vaults._SH_ETH_VAULT_ADDRESS,
            bytes.fromhex("704cfb08969048a8dff298b214f959791d8da509"),
        )
        # https://basescan.org/address/0x5e6fc406960a1C2d9Ab6813fF1c914c6836bC53E
        self.assertEqual(
            yielding_vaults._BASE_SH_USDC_VAULT_ADDRESS,
            bytes.fromhex("5e6fc406960a1c2d9ab6813ff1c914c6836bc53e"),
        )
        # https://basescan.org/address/0x4EDC6aB1964e25eb2C202AB9F201E9548BAa53dF
        self.assertEqual(
            yielding_vaults._BASE_SH_ETH_VAULT_ADDRESS,
            bytes.fromhex("4edc6ab1964e25eb2c202ab9f201e9548baa53df"),
        )

    def test_known_token_addresses(self):
        # https://etherscan.io/token/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
        self.assertEqual(
            yielding_vaults._USDC_ADDRESS,
            bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"),
        )
        # https://etherscan.io/token/0xdAC17F958D2ee523a2206206994597C13D831ec7
        self.assertEqual(
            yielding_vaults._USDT_ADDRESS,
            bytes.fromhex("dac17f958d2ee523a2206206994597c13d831ec7"),
        )
        # https://etherscan.io/token/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
        self.assertEqual(
            yielding_vaults._WETH_ADDRESS,
            bytes.fromhex("c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
        )
        # https://basescan.org/token/0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
        self.assertEqual(
            yielding_vaults._BASE_USDC_ADDRESS,
            bytes.fromhex("833589fcd6edb6e08f4c7c32d4f71b54bda02913"),
        )
        # https://basescan.org/token/0x4200000000000000000000000000000000000006
        self.assertEqual(
            yielding_vaults._BASE_WETH_ADDRESS,
            bytes.fromhex("4200000000000000000000000000000000000006"),
        )


if __name__ == "__main__":
    unittest.main()
