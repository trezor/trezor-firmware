import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
import trezor.utils

from trezor.crypto import hashlib

class TestCryptoSha3_256(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html

    def test_digest(self):
        self.assertEqual(hashlib.sha3_256(b'').digest(), trezor.utils.unhexlify('a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a'))
        self.assertEqual(hashlib.sha3_256(b'abc').digest(), trezor.utils.unhexlify('3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532'))
        self.assertEqual(hashlib.sha3_256(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq').digest(), trezor.utils.unhexlify('41c0dba2a9d6240849100376a8235e2c82e1b9998a999e21db32dd97496d3376'))
        self.assertEqual(hashlib.sha3_256(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu').digest(), trezor.utils.unhexlify('916f6061fe879741ca6469b43971dfdb28b1a32dc36cb3254e812be27aad1d18'))

    def test_update(self):
        x = hashlib.sha3_256()
        self.assertEqual(x.digest(), trezor.utils.unhexlify('a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a'))

        x = hashlib.sha3_256()
        x.update(b'abc')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532'))

        x = hashlib.sha3_256()
        x.update(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('41c0dba2a9d6240849100376a8235e2c82e1b9998a999e21db32dd97496d3376'))

        x = hashlib.sha3_256()
        x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('916f6061fe879741ca6469b43971dfdb28b1a32dc36cb3254e812be27aad1d18'))

        x = hashlib.sha3_256()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('5c8875ae474a3634ba4fd55ec85bffd661f32aca75c6d699d0cdcb6c115891c1'))

        '''
        x = hashlib.sha3_256()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('ecbbc42cbf296603acb2c6bc0410ef4378bafb24b710357f12df607758b33e2b'))
        '''

    def test_digest_multi(self):
        x = hashlib.sha3_256()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)

if __name__ == '__main__':
    unittest.main()
