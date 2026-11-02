# flake8: noqa: F403,F405
from common import *  # isort:skip

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
            self.assertAlmostEqual(c[r], 1000, delta=200)

    def test_bytes_length(self):
        for length in range(1024 + 1):
            lst = random.bytes(length)
            self.assertEqual(len(lst), length)

    def test_bytes_big_length(self):
        with self.assertRaises(ValueError):
            random.bytes(10000)

    def test_bytes_uniform(self):
        for _ in range(100):
            c = {}
            for h in "0123456789abcdef":
                c[h] = 0
            for _ in range(8):
                b = random.bytes(1000)
                for h in b.hex():
                    c[h] += 1
            for h in "0123456789abcdef":
                self.assertAlmostEqual(c[h], 1000, delta=200)

    def test_shuffle(self):
        for length in range(256 + 1):
            lst = list(range(length))
            random.shuffle(lst)
            self.assertEqual(len(lst), length)
            self.assertEqual(sorted(lst), list(range(length)))


if __name__ == "__main__":
    unittest.main()
