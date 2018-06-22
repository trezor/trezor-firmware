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
            c3 = coins.by_address_type(a)
            self.assertEqual(c1, c2)
            self.assertEqual(c1, c3)
            self.assertEqual(c2, c3)

    def test_failure(self):
        with self.assertRaises(ValueError):
            coins.by_shortcut('XXX')
        with self.assertRaises(ValueError):
            coins.by_name('XXXXX')
        with self.assertRaises(ValueError):
            coins.by_address_type(1234)


if __name__ == '__main__':
    unittest.main()
