import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
from ubinascii import hexlify

from trezor.crypto import random

class TestCryptoRandom(unittest.TestCase):

    def test_uniform(self):
        c = {}
        for i in range(15):
            c[i] = 0
        for _ in range(15000):
            r = random.uniform(15)
            c[r] += 1
        for i in range(15):
            self.assertTrue(c[r] > 900)
            self.assertTrue(c[r] < 1100)

    def test_bytes_length(self):
        for l in range(1024 + 1):
            lst = random.bytes(l)
            self.assertEqual(len(lst), l)

    def test_bytes_uniform(self):
        for _ in range(100):
            b = random.bytes(8000)
            c = {}
            for h in '0123456789abcdef':
                c[h] = 0
            for h in hexlify(b):
                c[chr(h)] += 1
            for h in '0123456789abcdef':
                self.assertTrue(c[h] > 900)
                self.assertTrue(c[h] < 1100)


    def test_shuffle(self):
        for l in range(256 + 1):
            lst = list(range(l))
            random.shuffle(lst)
            self.assertEqual(len(lst), l)
            self.assertEqual(sorted(lst), list(range(l)))

if __name__ == '__main__':
    unittest.main()
