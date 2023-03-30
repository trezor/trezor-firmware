from common import *

from trezor.crypto import hashlib


class TestCryptoSha1(unittest.TestCase):

    # vectors from https://www.di-mgt.com.au/sha_testvectors.html
    vectors = [
        (b'', 'da39a3ee5e6b4b0d3255bfef95601890afd80709'),
        (b'abc', 'a9993e364706816aba3e25717850c26c9cd0d89d'),
        (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', '84983e441c3bd26ebaae4aa1f95129e5e54670f1'),
        (b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu', 'a49b2446a02c645bf419f995b67091253a04a259')
    ]

    def test_digest(self):
        for b, d in self.vectors:
            self.assertEqual(hashlib.sha1(b).digest(), unhexlify(d))

    def test_update(self):
        for b, d in self.vectors:
            x = hashlib.sha1()
            x.update(b)
            self.assertEqual(x.digest(), unhexlify(d))

        x = hashlib.sha1()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), unhexlify('34aa973cd4c4daa4f61eeb2bdbad27316534016f'))

        '''
        x = hashlib.sha1()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), unhexlify('7789f0c9ef7bfc40d93311143dfbe69e2017f592'))
        '''

    def test_digest_multi(self):
        x = hashlib.sha1()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
