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

import unittest
import common

from trezorlib import messages_pb2 as proto

class TestDeviceWipe(common.TrezorTest):
    def test_wipe_device(self):
        self.setup_mnemonic_pin_passphrase()
        features = self.client.call_raw(proto.Initialize())

        self.assertEqual(features.initialized, True)
        self.assertEqual(features.pin_protection, True)
        self.assertEqual(features.passphrase_protection, True)
        device_id = features.device_id

        self.client.wipe_device()
        features = self.client.call_raw(proto.Initialize())

        self.assertEqual(features.initialized, False)
        self.assertEqual(features.pin_protection, False)
        self.assertEqual(features.passphrase_protection, False)
        self.assertNotEqual(features.device_id, device_id)

if __name__ == '__main__':
    unittest.main()
