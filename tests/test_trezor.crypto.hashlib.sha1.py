from common import *

from trezor.crypto import hashlib

class TestCryptoSha1(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html

    def test_digest(self):
        self.assertEqual(hashlib.sha1(b'').digest(), unhexlify('da39a3ee5e6b4b0d3255bfef95601890afd80709'))
        self.assertEqual(hashlib.sha1(b'abc').digest(), unhexlify('a9993e364706816aba3e25717850c26c9cd0d89d'))
        self.assertEqual(hashlib.sha1(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq').digest(), unhexlify('84983e441c3bd26ebaae4aa1f95129e5e54670f1'))
        self.assertEqual(hashlib.sha1(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu').digest(), unhexlify('a49b2446a02c645bf419f995b67091253a04a259'))

    def test_update(self):
        x = hashlib.sha1()
        self.assertEqual(x.digest(), unhexlify('da39a3ee5e6b4b0d3255bfef95601890afd80709'))

        x = hashlib.sha1()
        x.update(b'abc')
        self.assertEqual(x.digest(), unhexlify('a9993e364706816aba3e25717850c26c9cd0d89d'))

        x = hashlib.sha1()
        x.update(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
        self.assertEqual(x.digest(), unhexlify('84983e441c3bd26ebaae4aa1f95129e5e54670f1'))

        x = hashlib.sha1()
        x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu')
        self.assertEqual(x.digest(), unhexlify('a49b2446a02c645bf419f995b67091253a04a259'))

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
