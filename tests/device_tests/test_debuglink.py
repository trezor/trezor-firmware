# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

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
