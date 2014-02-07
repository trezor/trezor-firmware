import time
import unittest
import common

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as types

class TestPing(common.TrezorTest):

    def test_ping(self):

        res = self.client.ping('random data')
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', button_protection=True)
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', pin_protection=True)
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', passphrase_protection=True)
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', button_protection=True, pin_protection=True)
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', button_protection=True, passphrase_protection=True)
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', pin_protection=True, passphrase_protection=True)
        self.assertEqual(res, 'random data')

        res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
        self.assertEqual(res, 'random data')

if __name__ == '__main__':
    unittest.main()
