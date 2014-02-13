import unittest
import common
import time
from trezorlib import tools

class TestAddresses(common.TrezorTest):
    def test_public_ckd(self):
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin='',
                                            passphrase_protection=False,
                                            label='test',
                                            language='english')

        self.client.get_address('Bitcoin', [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            self.client.get_address('Bitcoin', range(depth))
            delay = time.time() - start
            expected = (depth + 1) * 0.25
            print "DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay
            self.assertLessEqual(delay, expected)

    def test_private_ckd(self):
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin='',
                                            passphrase_protection=False,
                                            label='test',
                                            language='english')

        self.client.get_address('Bitcoin', [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            self.client.get_address('Bitcoin', range(-depth, 0))
            delay = time.time() - start
            expected = (depth + 1) * 0.25
            print "DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay
            self.assertLessEqual(delay, expected)

if __name__ == '__main__':
    unittest.main()
