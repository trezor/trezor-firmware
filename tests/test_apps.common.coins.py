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
            c1 = coins.by_shortcut(s)
            c2 = coins.by_name(n)
            self.assertEqual(c1, c2)
            self.assertEqual(c1.address_type, a)

    def test_failure(self):
        with self.assertRaises(ValueError):
            coins.by_shortcut('XXX')
        with self.assertRaises(ValueError):
            coins.by_name('XXXXX')


if __name__ == '__main__':
    unittest.main()
