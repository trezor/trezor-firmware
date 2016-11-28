from __future__ import print_function

import unittest
import common
import time
from trezorlib import tools

class TestBip32Speed(common.TrezorTest):

    def test_public_ckd(self):
        self.setup_mnemonic_nopin_nopassphrase()

        self.client.get_address('Bitcoin', [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            self.client.get_address('Bitcoin', range(depth))
            delay = time.time() - start
            expected = (depth + 1) * 0.26
            print("DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay)
            self.assertLessEqual(delay, expected)

    def test_private_ckd(self):
        self.setup_mnemonic_nopin_nopassphrase()

        self.client.get_address('Bitcoin', [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            self.client.get_address('Bitcoin', range(-depth, 0))
            delay = time.time() - start
            expected = (depth + 1) * 0.26
            print("DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay)
            self.assertLessEqual(delay, expected)

    def test_cache(self):
        self.setup_mnemonic_nopin_nopassphrase()

        start = time.time()
        for x in range(10):
            self.client.get_address('Bitcoin', [x, 2, 3, 4, 5, 6, 7, 8])
        nocache_time = time.time() - start

        start = time.time()
        for x in range(10):
            self.client.get_address('Bitcoin', [1, 2, 3, 4, 5, 6, 7, x])
        cache_time = time.time() - start

        print("NOCACHE TIME", nocache_time)
        print("CACHED TIME", cache_time)

        # Cached time expected to be at least 2x faster
        self.assertLessEqual(cache_time, nocache_time / 2.)

if __name__ == '__main__':
    unittest.main()
