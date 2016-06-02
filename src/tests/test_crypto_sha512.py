import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
from ubinascii import unhexlify

from trezor.crypto import hashlib

class TestCryptoSha512(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html

    def test_digest(self):
        self.assertEqual(hashlib.sha512(b'').digest(), unhexlify('cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'))
        self.assertEqual(hashlib.sha512(b'abc').digest(), unhexlify('ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f'))
        self.assertEqual(hashlib.sha512(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq').digest(), unhexlify('204a8fc6dda82f0a0ced7beb8e08a41657c16ef468b228a8279be331a703c33596fd15c13b1b07f9aa1d3bea57789ca031ad85c7a71dd70354ec631238ca3445'))
        self.assertEqual(hashlib.sha512(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu').digest(), unhexlify('8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909'))

    def test_update(self):
        x = hashlib.sha512()
        self.assertEqual(x.digest(), unhexlify('cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'))

        x = hashlib.sha512()
        x.update(b'abc')
        self.assertEqual(x.digest(), unhexlify('ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f'))

        x = hashlib.sha512()
        x.update(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
        self.assertEqual(x.digest(), unhexlify('204a8fc6dda82f0a0ced7beb8e08a41657c16ef468b228a8279be331a703c33596fd15c13b1b07f9aa1d3bea57789ca031ad85c7a71dd70354ec631238ca3445'))

        x = hashlib.sha512()
        x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu')
        self.assertEqual(x.digest(), unhexlify('8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909'))

        x = hashlib.sha512()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), unhexlify('e718483d0ce769644e2e42c7bc15b4638e1f98b13b2044285632a803afa973ebde0ff244877ea60a4cb0432ce577c31beb009c5c2c49aa2e4eadb217ad8cc09b'))

        '''
        x = hashlib.sha512()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), unhexlify('b47c933421ea2db149ad6e10fce6c7f93d0752380180ffd7f4629a712134831d77be6091b819ed352c2967a2e2d4fa5050723c9630691f1a05a7281dbe6c1086'))
        '''

    def test_digest_multi(self):
        x = hashlib.sha512()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)

if __name__ == '__main__':
    unittest.main()
