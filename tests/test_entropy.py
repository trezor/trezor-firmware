import unittest
import common
import math

from trezorlib import messages_pb2 as messages

def entropy(data):
    counts = {}
    for c in data:
        if c in counts:
            counts[c] += 1
        else:
            counts[c] = 1
    e = 0
    for k,v in counts.iteritems():
        p = 1.0 * v / len(data)
        e -= p * math.log(p, 256)
    return e

class TestEntropy(common.TrezorTest):

    def test_entropy(self):
        for l in [0, 1, 2, 3, 4, 5, 8, 9, 16, 17, 32, 33, 64, 65, 128, 129, 256, 257, 512, 513, 1024]:
            ent = self.client.get_entropy(l)
            self.assertTrue(len(ent) >= l)
            print 'entropy = ', entropy(ent)

if __name__ == '__main__':
    unittest.main()
