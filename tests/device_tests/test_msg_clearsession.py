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

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as proto_types

class TestMsgClearsession(common.TrezorTest):

    def test_clearsession(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            # pin and passphrase are cached
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

        self.client.clear_session()

        # session cache is cleared
        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            # pin and passphrase are cached
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

if __name__ == '__main__':
    unittest.main()
