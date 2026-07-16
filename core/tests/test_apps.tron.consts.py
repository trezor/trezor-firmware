# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto import base58

    from apps.tron import consts


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestTronConsts(unittest.TestCase):
    def test_known_token_addresses(self):
        # Verify that the hardcoded TRC-20 address bytes match the published
        # base58check addresses, so a typo in the literals cannot silently
        # route users to a wrong token.
        expected = {
            # https://shasta.tronscan.org/#/token20/TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs
            consts._SHASTA_USDT_ADDRESS: "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs",
            # https://tronscan.org/#/token20/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
            consts._USDT_ADDRESS: "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            # https://tronscan.org/#/token20/TXDk8mbtRbXeYuMNS83CfKPaYYT8XWv9Hz
            consts._USDD_ADDRESS: "TXDk8mbtRbXeYuMNS83CfKPaYYT8XWv9Hz",
            # https://tronscan.org/#/token20/TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S
            consts._SUN_ADDRESS: "TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S",
            # https://tronscan.org/#/token20/TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9
            consts._JST_ADDRESS: "TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9",
            # https://tronscan.org/#/token20/TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4
            consts._BTT_ADDRESS: "TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4",
            # https://tronscan.org/#/token20/TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7
            consts._WIN_ADDRESS: "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            # https://tronscan.org/#/token20/TYhWwKpw43ENFWBTGpzLHn3882f2au7SMi
            consts._WBTC_ADDRESS: "TYhWwKpw43ENFWBTGpzLHn3882f2au7SMi",
            # https://tronscan.org/#/token20/THb4CqiFdwNHsWsQCs4JhzwjMWys4aqCbF
            consts._ETH_TRON_ADDRESS: "THb4CqiFdwNHsWsQCs4JhzwjMWys4aqCbF",
            # https://tronscan.org/#/token20/TPFqcBAaaUMCSVRCqPaQ9QnzKhmuoLR6Rc
            consts._USD1_ADDRESS: "TPFqcBAaaUMCSVRCqPaQ9QnzKhmuoLR6Rc",
            # https://tronscan.org/#/token20/TUPM7K8REVzD2UdV4R5fe5M8XbnR2DdoJ6
            consts._HTX_ADDRESS: "TUPM7K8REVzD2UdV4R5fe5M8XbnR2DdoJ6",
            # https://tronscan.org/#/token20/TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4
            consts._TUSD_ADDRESS: "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4",
            # https://tronscan.org/#/token20/TFptbWaARrWTX5Yvy3gNG5Lm8BmhPx82Bt
            consts._WBT_ADDRESS: "TFptbWaARrWTX5Yvy3gNG5Lm8BmhPx82Bt",
            # https://tronscan.org/#/token20/TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR
            consts._WTRX_ADDRESS: "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR",
            # https://tronscan.org/#/token20/TKkeiboTkxXKJpbmVFbv4a8ov5rAfRDMf9
            consts._SUNOLD_ADDRESS: "TKkeiboTkxXKJpbmVFbv4a8ov5rAfRDMf9",
            # https://tronscan.org/#/token20/TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq
            consts._AINFT_ADDRESS: "TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq",
            # https://tronscan.org/#/token20/TU3kjFuhtEo42tsCBtfYUAZxoqQ4yuSLQ5
            consts._STRX_ADDRESS: "TU3kjFuhtEo42tsCBtfYUAZxoqQ4yuSLQ5",
            # https://tronscan.org/#/token20/TVj7RNVHy6thbM7BWdSe9G6gXwKhjhdNZS
            consts._KLEVER_ADDRESS: "TVj7RNVHy6thbM7BWdSe9G6gXwKhjhdNZS",
        }
        for address_bytes, expected_b58 in expected.items():
            self.assertEqual(
                base58.encode_check(address_bytes),
                expected_b58,
                msg=f"mismatch for {expected_b58}",
            )


if __name__ == "__main__":
    unittest.main()
