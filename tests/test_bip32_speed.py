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
            print "DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay
            self.assertLessEqual(delay, expected)

    def test_private_ckd(self):
        self.setup_mnemonic_nopin_nopassphrase()

        self.client.get_address('Bitcoin', [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            self.client.get_address('Bitcoin', range(-depth, 0))
            delay = time.time() - start
            expected = (depth + 1) * 0.26
            print "DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay
            self.assertLessEqual(delay, expected)

if __name__ == '__main__':
    unittest.main()
