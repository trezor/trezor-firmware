from common import *

from trezor.crypto import hashlib


class TestCryptoSha3_256(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html
    vectors = [
        (b'', 'a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a'),
        (b'abc', '3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532'),
        (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', '41c0dba2a9d6240849100376a8235e2c82e1b9998a999e21db32dd97496d3376'),
        (b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu', '916f6061fe879741ca6469b43971dfdb28b1a32dc36cb3254e812be27aad1d18'),
    ]

    vectors_keccak = [
        (b'', 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'),
        (b'abc', '4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45'),
        (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', '45d3b367a6904e6e8d502ee04999a7c27647f91fa845d456525fd352ae3d7371'),
        (b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu', 'f519747ed599024f3882238e5ab43960132572b7345fbeb9a90769dafd21ad67'),
    ]

    def test_digest(self):
        for b, d in self.vectors:
            self.assertEqual(hashlib.sha3_256(b).digest(), unhexlify(d))

    def test_digest_keccak(self):
        for b, d in self.vectors_keccak:
            self.assertEqual(hashlib.sha3_256(b, keccak=True).digest(), unhexlify(d))

    def test_update(self):
        for b, d in self.vectors:
            x = hashlib.sha3_256()
            x.update(b)
            self.assertEqual(x.digest(), unhexlify(d))

        x = hashlib.sha3_256()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), unhexlify('5c8875ae474a3634ba4fd55ec85bffd661f32aca75c6d699d0cdcb6c115891c1'))

        '''
        x = hashlib.sha3_256()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), unhexlify('ecbbc42cbf296603acb2c6bc0410ef4378bafb24b710357f12df607758b33e2b'))
        '''

    def test_update_keccak(self):
        for b, d in self.vectors_keccak:
            x = hashlib.sha3_256(keccak=True)
            x.update(b)
            self.assertEqual(x.digest(), unhexlify(d))

    def test_digest_multi(self):
        x = hashlib.sha3_256()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)

    def test_digest_multi_keccak(self):
        x = hashlib.sha3_256(keccak=True)
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
