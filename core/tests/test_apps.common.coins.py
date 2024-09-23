from common import *  # isort:skip

from apps.common import coins


class TestCoins(unittest.TestCase):
    def test_bitcoin(self):
        ref = [
            ("BTC", "Bitcoin", 0),
            ("TEST", "Testnet", 111),
            ("REGTEST", "Regtest", 111),
        ]
        for s, n, a in ref:
            c = coins.by_name(n)
            self.assertEqual(c.address_type, a)
            self.assertEqual(c.coin_shortcut, s)

    @unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
    def test_altcoins(self):
        ref = [
            ("LTC", "Litecoin", 48),
            ("ZEC", "Zcash", 7352),
            ("TAZ", "Zcash Testnet", 7461),
        ]
        if utils.INTERNAL_MODEL in ("T2T1",):
            ref.extend(
                [
                    ("NMC", "Namecoin", 52),
                    ("DASH", "Dash", 76),
                ]
            )
        for s, n, a in ref:
            c = coins.by_name(n)
            self.assertEqual(c.address_type, a)
            self.assertEqual(c.coin_shortcut, s)

    def test_failure(self):
        with self.assertRaises(ValueError):
            coins.by_name("XXXXX")


if __name__ == "__main__":
    unittest.main()
