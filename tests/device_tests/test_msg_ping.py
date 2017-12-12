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

from trezorlib import messages as proto


class TestPing(common.TrezorTest):

    def test_ping(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses([proto.Success()])
            res = self.client.ping('random data')
            self.assertEqual(res, 'random data')

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall), proto.Success()])
            res = self.client.ping('random data', button_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            self.client.set_expected_responses([proto.PinMatrixRequest(), proto.Success()])
            res = self.client.ping('random data', pin_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            self.client.set_expected_responses([proto.PassphraseRequest(), proto.Success()])
            res = self.client.ping('random data', passphrase_protection=True)
            self.assertEqual(res, 'random data')

    def test_ping_caching(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall), proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            # pin and passphrase are cached
            self.client.set_expected_responses([proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')
