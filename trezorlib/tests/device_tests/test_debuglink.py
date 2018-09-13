# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import messages as proto

from .common import TrezorTest


@pytest.mark.skip_t2
class TestDebuglink(TrezorTest):
    def test_layout(self):
        layout = self.client.debug.state().layout
        assert len(layout) == 1024

    def test_mnemonic(self):
        self.setup_mnemonic_nopin_nopassphrase()
        mnemonic = self.client.debug.state().mnemonic
        assert mnemonic == self.mnemonic12

    def test_pin(self):
        self.setup_mnemonic_pin_passphrase()

        # Manually trigger PinMatrixRequest
        resp = self.client.call_raw(proto.Ping(message="test", pin_protection=True))
        assert isinstance(resp, proto.PinMatrixRequest)

        pin, matrix = self.client.debug.read_pin()
        assert pin == "1234"
        assert matrix != ""

        pin_encoded = self.client.debug.read_pin_encoded()
        resp = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(resp, proto.Success)
