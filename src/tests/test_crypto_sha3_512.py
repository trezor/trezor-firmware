import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
import trezor.utils

from trezor.crypto import hashlib

class TestCryptoSha3_512(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html

    def test_digest(self):
        self.assertEqual(hashlib.sha3_512(b'').digest(), trezor.utils.unhexlify('a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26'))
        self.assertEqual(hashlib.sha3_512(b'abc').digest(), trezor.utils.unhexlify('b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0'))
        self.assertEqual(hashlib.sha3_512(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq').digest(), trezor.utils.unhexlify('04a371e84ecfb5b8b77cb48610fca8182dd457ce6f326a0fd3d7ec2f1e91636dee691fbe0c985302ba1b0d8dc78c086346b533b49c030d99a27daf1139d6e75e'))
        self.assertEqual(hashlib.sha3_512(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu').digest(), trezor.utils.unhexlify('afebb2ef542e6579c50cad06d2e578f9f8dd6881d7dc824d26360feebf18a4fa73e3261122948efcfd492e74e82e2189ed0fb440d187f382270cb455f21dd185'))

    def test_update(self):
        x = hashlib.sha3_512()
        self.assertEqual(x.digest(), trezor.utils.unhexlify('a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26'))

        x = hashlib.sha3_512()
        x.update(b'abc')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0'))

        x = hashlib.sha3_512()
        x.update(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('04a371e84ecfb5b8b77cb48610fca8182dd457ce6f326a0fd3d7ec2f1e91636dee691fbe0c985302ba1b0d8dc78c086346b533b49c030d99a27daf1139d6e75e'))

        x = hashlib.sha3_512()
        x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('afebb2ef542e6579c50cad06d2e578f9f8dd6881d7dc824d26360feebf18a4fa73e3261122948efcfd492e74e82e2189ed0fb440d187f382270cb455f21dd185'))

        x = hashlib.sha3_512()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('3c3a876da14034ab60627c077bb98f7e120a2a5370212dffb3385a18d4f38859ed311d0a9d5141ce9cc5c66ee689b266a8aa18ace8282a0e0db596c90b0a7b87'))

        '''
        x = hashlib.sha3_512()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('235ffd53504ef836a1342b488f483b396eabbfe642cf78ee0d31feec788b23d0d18d5c339550dd5958a500d4b95363da1b5fa18affc1bab2292dc63b7d85097c'))
        '''

    def test_digest_multi(self):
        x = hashlib.sha3_512()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)

if __name__ == '__main__':
    unittest.main()
