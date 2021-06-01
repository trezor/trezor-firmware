from common import *

if not utils.BITCOIN_ONLY:
    from trezor.messages import NEMMosaic
    from apps.nem.mosaic.helpers import get_mosaic_definition
    from apps.nem.transfer import *
    from apps.nem.transfer.serialize import *


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNemMosaic(unittest.TestCase):

    def test_get_mosaic_definition(self):
        m = get_mosaic_definition("nem", "xem", 104)
        self.assertEqual(m["name"], "NEM")
        self.assertEqual(m["ticker"], " XEM")

        m = get_mosaic_definition("nem", "xxx", 104)
        self.assertEqual(m, None)

        m = get_mosaic_definition("aaaa", "xxx", 104)
        self.assertEqual(m, None)

        m = get_mosaic_definition("pacnem", "cheese", 104)
        self.assertEqual(m["name"], "PacNEM Score Tokens")
        self.assertEqual(m["ticker"], " PAC:CHS")
        self.assertEqual(m["fee"], 100)

    def test_mosaic_canonicalization(self):
        a = NEMMosaic()
        a.namespace = 'abc'
        a.quantity = 3
        a.mosaic = 'mosaic'
        b = NEMMosaic()
        b.namespace = 'abc'
        b.quantity = 4
        b.mosaic = 'a'
        c = NEMMosaic()
        c.namespace = 'zzz'
        c.quantity = 3
        c.mosaic = 'mosaic'
        d = NEMMosaic()
        d.namespace = 'abc'
        d.quantity = 8
        d.mosaic = 'mosaic'
        e = NEMMosaic()
        e.namespace = 'aaa'
        e.quantity = 1
        e.mosaic = 'mosaic'
        f = NEMMosaic()
        f.namespace = 'aaa'
        f.quantity = 1
        f.mosaic = 'mosaicz'
        g = NEMMosaic()
        g.namespace = 'zzz'
        g.quantity = 30
        g.mosaic = 'mosaic'

        res = canonicalize_mosaics([a, b, c, d, e, f, g])
        self.assertEqual(res, [e, f, b, a, c])
        self.assertEqual(res[2].quantity, b.quantity)
        self.assertEqual(res[3].quantity, 3 + 8)  # a + d
        self.assertEqual(res[4].quantity, 3 + 30)  # c + g

    def test_mosaic_merge(self):
        a = NEMMosaic()
        a.namespace = 'abc'
        a.quantity = 1
        a.mosaic = 'mosaic'
        b = NEMMosaic()
        b.namespace = 'abc'
        b.quantity = 1
        b.mosaic = 'mosaic'

        merged = merge_mosaics([a, b])
        self.assertEqual(merged[0].quantity, 2)
        self.assertEqual(len(merged), 1)

        a.quantity = 1
        b.quantity = 10
        merged = merge_mosaics([a, b])
        self.assertEqual(merged[0].quantity, 11)

        a.namespace = 'abcdef'
        merged = merge_mosaics([a, b])
        self.assertEqual(len(merged), 2)

        c = NEMMosaic()
        c.namespace = 'abc'
        c.mosaic = 'xxx'
        c.quantity = 2
        merged = merge_mosaics([a, b, c])
        self.assertEqual(len(merged), 3)

        a.namespace = 'abcdef'
        a.quantity = 1
        a.mosaic = 'mosaic'
        b.namespace = 'abc'
        b.quantity = 2
        b.mosaic = 'mosaic'
        c.namespace = 'abc'
        c.mosaic = 'mosaic'
        c.quantity = 3
        merged = merge_mosaics([a, b, c])
        self.assertEqual(merged[0].quantity, 1)
        self.assertEqual(merged[1].quantity, 5)
        self.assertEqual(len(merged), 2)

        a.namespace = 'abc'
        a.quantity = 1
        a.mosaic = 'mosaic'
        b.namespace = 'abc'
        b.quantity = 2
        b.mosaic = 'mosaic'
        c.namespace = 'abc'
        c.mosaic = 'mosaic'
        c.quantity = 3
        merged = merge_mosaics([a, b, c])
        self.assertEqual(merged[0].quantity, 6)
        self.assertEqual(len(merged), 1)

    def test_mosaic_sort(self):
        a = NEMMosaic()
        a.namespace = 'abcz'
        a.quantity = 1
        a.mosaic = 'mosaic'
        b = NEMMosaic()
        b.namespace = 'abca'
        b.quantity = 1
        b.mosaic = 'mosaic'
        res = sort_mosaics([a, b])
        self.assertListEqual(res, [b, a])

        a.namespace = ''
        b.namespace = 'a.b.c'
        res = sort_mosaics([a, b])
        self.assertListEqual(res, [a, b])

        a.namespace = 'z.z.z'
        b.namespace = 'a.b.c'
        res = sort_mosaics([a, b])
        self.assertListEqual(res, [b, a])

        a.namespace = 'a'
        b.namespace = 'a'
        a.mosaic = 'mosaic'
        b.mosaic = 'mosaic'
        res = sort_mosaics([a, b])
        self.assertListEqual(res, [a, b])

        a.mosaic = 'www'
        b.mosaic = 'aaa'
        res = sort_mosaics([a, b])
        self.assertListEqual(res, [b, a])

        c = NEMMosaic()
        c.namespace = 'a'
        c.mosaic = 'zzz'
        res = sort_mosaics([a, b, c])
        self.assertListEqual(res, [b, a, c])

        c.mosaic = 'bbb'
        res = sort_mosaics([a, b, c])
        self.assertListEqual(res, [b, c, a])


if __name__ == '__main__':
    unittest.main()
