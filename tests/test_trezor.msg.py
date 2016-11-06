from common import *

from trezor.crypto import random

from trezor import msg

class TestMsg(unittest.TestCase):

    def test_set_get_interfaces(self):
        ifaces = msg.get_interfaces()
        self.assertEqual(ifaces, ())
        for n in range(1, 9):
            ifaces = tuple((random.uniform(0x10000) for _ in range(n)))
            msg.set_interfaces(ifaces)
            ifaces2 = msg.get_interfaces()
            self.assertEqual(ifaces, ifaces2)

if __name__ == '__main__':
    unittest.main()
