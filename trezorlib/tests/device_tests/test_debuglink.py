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

from .common import *

from trezorlib import messages as proto


@pytest.mark.skip_t2
class TestDebuglink(TrezorTest):

    def test_layout(self):
        layout = self.client.debug.read_layout()
        assert len(layout) == 1024

    def test_mnemonic(self):
        self.setup_mnemonic_nopin_nopassphrase()
        mnemonic = self.client.debug.read_mnemonic()
        assert mnemonic == self.mnemonic12

    def test_pin(self):
        self.setup_mnemonic_pin_passphrase()

        # Manually trigger PinMatrixRequest
        resp = self.client.call_raw(proto.Ping(message='test', pin_protection=True))
        assert isinstance(resp, proto.PinMatrixRequest)

        pin = self.client.debug.read_pin()
        assert pin[0] == '1234'
        assert pin[1] != ''

        pin_encoded = self.client.debug.read_pin_encoded()
        resp = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(resp, proto.Success)
