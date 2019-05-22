from common import *

from apps.common import coins


class TestCoins(unittest.TestCase):

    def test_coins(self):
        ref = [
            ('BTC', 'Bitcoin', 0),
            ('NMC', 'Namecoin', 52),
            ('LTC', 'Litecoin', 48),
            ('DASH', 'Dash', 76),
            ('ZEC', 'Zcash', 7352),
            ('TAZ', 'Zcash Testnet', 7461),
        ]
        for s, n, a in ref:
            c = coins.by_name(n)
            self.assertEqual(c.address_type, a)
            self.assertEqual(c.coin_shortcut, s)

    def test_failure(self):
        with self.assertRaises(ValueError):
            coins.by_name('XXXXX')


if __name__ == '__main__':
    unittest.main()
