import unittest
import common
import math

from trezorlib import messages_pb2 as messages

def entropy(data):
    e = 0
    for i in range(256):
        p = 0
        for c in data:
            if ord(c) == i:
                p += 1
        if p == 0:
            continue
        p = 1.0 * p / len(data)
        e -= p * math.log(p, 256)
    return e

class TestEntropy(common.TrezorTest):

    def test_entropy(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin='',
                                            passphrase_protection=False,
                                            label='test',
                                            language='english')

        for l in [0, 1, 2, 3, 4, 5, 8, 9, 16, 17, 32, 33, 64, 65, 128, 129, 256, 257, 512, 513, 1024]:
            ent = self.client.get_entropy(l)
            self.assertTrue(len(ent) >= l)
            print 'entropy = ', entropy(ent)

if __name__ == '__main__':
    unittest.main()
