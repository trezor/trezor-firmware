import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
import trezor.utils

from trezor.crypto import hashlib

class TestCryptoRipemd160(unittest.TestCase):

    # vectors from http://homes.esat.kuleuven.be/~bosselae/ripemd160.html

    def test_digest(self):
        self.assertEqual(hashlib.ripemd160(b'').digest(), trezor.utils.unhexlify('9c1185a5c5e9fc54612808977ee8f548b2258d31'))
        self.assertEqual(hashlib.ripemd160(b'a').digest(), trezor.utils.unhexlify('0bdc9d2d256b3ee9daae347be6f4dc835a467ffe'))
        self.assertEqual(hashlib.ripemd160(b'abc').digest(), trezor.utils.unhexlify('8eb208f7e05d987a9b044a8e98c6b087f15a0bfc'))
        self.assertEqual(hashlib.ripemd160(b'message digest').digest(), trezor.utils.unhexlify('5d0689ef49d2fae572b881b123a85ffa21595f36'))
        self.assertEqual(hashlib.ripemd160(b'abcdefghijklmnopqrstuvwxyz').digest(), trezor.utils.unhexlify('f71c27109c692c1b56bbdceb5b9d2865b3708dbc'))
        self.assertEqual(hashlib.ripemd160(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq').digest(), trezor.utils.unhexlify('12a053384a9c0c88e405a06c27dcf49ada62eb2b'))
        self.assertEqual(hashlib.ripemd160(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789').digest(), trezor.utils.unhexlify('b0e20b6e3116640286ed3a87a5713079b21f5189'))
        self.assertEqual(hashlib.ripemd160(b'12345678901234567890123456789012345678901234567890123456789012345678901234567890').digest(), trezor.utils.unhexlify('9b752e45573d4b39f4dbd3323cab82bf63326bfb'))

    def test_update(self):
        x = hashlib.ripemd160()
        self.assertEqual(x.digest(), trezor.utils.unhexlify('9c1185a5c5e9fc54612808977ee8f548b2258d31'))

        x = hashlib.ripemd160()
        x.update(b'a')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('0bdc9d2d256b3ee9daae347be6f4dc835a467ffe'))

        x = hashlib.ripemd160()
        x.update(b'abc')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('8eb208f7e05d987a9b044a8e98c6b087f15a0bfc'))

        x = hashlib.ripemd160()
        x.update(b'message digest')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('5d0689ef49d2fae572b881b123a85ffa21595f36'))

        x = hashlib.ripemd160()
        x.update(b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('f71c27109c692c1b56bbdceb5b9d2865b3708dbc'))

        x = hashlib.ripemd160()
        x.update(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('12a053384a9c0c88e405a06c27dcf49ada62eb2b'))

        x = hashlib.ripemd160()
        x.update(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('b0e20b6e3116640286ed3a87a5713079b21f5189'))

        x = hashlib.ripemd160()
        for i in range(8):
            x.update(b'1234567890')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('9b752e45573d4b39f4dbd3323cab82bf63326bfb'))

    def test_digest_multi(self):
        x = hashlib.ripemd160()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)

if __name__ == '__main__':
    unittest.main()
