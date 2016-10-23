import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
from ubinascii import unhexlify

from trezor.crypto.curve import curve25519
from trezor.crypto import random

class TestCryptoCurve25519(unittest.TestCase):

    vectors = [
        ('38c9d9b17911de26ed812f5cc19c0029e8d016bcbc6078bc9db2af33f1761e4a', '311b6248af8dabec5cc81eac5bf229925f6d218a12e0547fb1856e015cc76f5d', 'a93dbdb23e5c99da743e203bd391af79f2b83fb8d0fd6ec813371c71f08f2d4d'),
    ]

    def test_multiply(self):
        for sk, pk, session in self.vectors:
            session2 = curve25519.multiply(unhexlify(sk), unhexlify(pk))
            self.assertEqual(session2, unhexlify(session))

    def test_multiply_random(self):
        for _ in range(100):
            sk1 = bytearray(random.bytes(32))
            sk2 = bytearray(random.bytes(32))
            # taken from https://cr.yp.to/ecdh.html
            sk1[0] &= 248 ; sk1[31] &= 127 ; sk1[31] |= 64
            sk2[0] &= 248 ; sk2[31] &= 127 ; sk2[31] |= 64
            pk1 = curve25519.publickey(sk1)
            pk2 = curve25519.publickey(sk2)
            session1 = curve25519.multiply(sk1, pk2)
            session2 = curve25519.multiply(sk2, pk1)
            self.assertEqual(session1, session2)

if __name__ == '__main__':
    unittest.main()
