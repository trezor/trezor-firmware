import time
import unittest
import common
import binascii

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as types
from trezorlib.client import PinException

class TestDebugLink(common.TrezorTest):

    def test_layout(self):
        layout = self.client.debug.read_layout()
        self.assertEqual(len(layout), 1024)

    def test_mnemonic(self):
        mnemonic = self.client.debug.read_mnemonic()
        self.assertEqual(mnemonic, self.mnemonic1)

    def test_node(self):
        node = self.client.debug.read_node()
        self.assertIsNotNone(node)

if __name__ == '__main__':
    unittest.main()
