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
        self.setup_mnemonic_nopin_nopassphrase()
        mnemonic = self.client.debug.read_mnemonic()
        self.assertEqual(mnemonic, self.mnemonic12)

    def test_node(self):
        self.setup_mnemonic_nopin_nopassphrase()
        node = self.client.debug.read_node()
        self.assertIsNotNone(node)

    def test_pin(self):
        self.setup_mnemonic_pin_passphrase()

        # Manually trigger PinMatrixRequest
        resp = self.client.call_raw(proto.Ping(message='test', pin_protection=True))
        self.assertIsInstance(resp, proto.PinMatrixRequest)

        pin = self.client.debug.read_pin()
        self.assertEqual(pin[0], '1234')
        self.assertNotEqual(pin[1], '')

        pin_encoded = self.client.debug.read_pin_encoded()
        resp = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        self.assertIsInstance(resp, proto.Success)

if __name__ == '__main__':
    unittest.main()
