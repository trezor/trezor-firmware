from common import *

from trezor.crypto.curve import curve25519


class TestCryptoCurve25519(unittest.TestCase):

    vectors = [
        ('38c9d9b17911de26ed812f5cc19c0029e8d016bcbc6078bc9db2af33f1761e4a', '311b6248af8dabec5cc81eac5bf229925f6d218a12e0547fb1856e015cc76f5d', 'a93dbdb23e5c99da743e203bd391af79f2b83fb8d0fd6ec813371c71f08f2d4d'),
    ]

    def test_generate_secret(self):
        for _ in range(100):
            sk = curve25519.generate_secret()
            self.assertTrue(len(sk) == 32)
            self.assertTrue(sk[0] & 7 == 0 and sk[31] & 128 == 0 and sk[31] & 64 == 64)

    def test_multiply(self):
        for sk, pk, session in self.vectors:
            session2 = curve25519.multiply(unhexlify(sk), unhexlify(pk))
            self.assertEqual(session2, unhexlify(session))

    def test_multiply_random(self):
        for _ in range(100):
            sk1 = curve25519.generate_secret()
            sk2 = curve25519.generate_secret()
            pk1 = curve25519.publickey(sk1)
            pk2 = curve25519.publickey(sk2)
            session1 = curve25519.multiply(sk1, pk2)
            session2 = curve25519.multiply(sk2, pk1)
            self.assertEqual(session1, session2)


if __name__ == '__main__':
    unittest.main()
