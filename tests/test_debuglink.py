import time
import unittest
import common
import binascii

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as types
from trezorlib.client import PinException

class TestDebugLink(common.TrezorTest):

    def test_layout(self):
        layout = self.client.debuglink.read_layout()
        print binascii.hexlify(layout)

    def test_mnemonic(self):
        mnemonic = self.client.debuglink.read_mnemonic()
        print mnemonic

    def test_node(self):
        node = self.client.debuglink.read_node()
        print node

if __name__ == '__main__':
    unittest.main()
