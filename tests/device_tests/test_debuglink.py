# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from trezorlib import debuglink, messages

from ..common import MNEMONIC12


@pytest.mark.skip_t2
class TestDebuglink:
    def test_layout(self, client):
        layout = client.debug.state().layout
        assert len(layout) == 1024

    # mnemonic_secret is not available when the device is locked, and the client fixture
    # locks the device after initialization.
    # It is easier to request an unintialized client and load it manually.
    @pytest.mark.setup_client(uninitialized=True)
    def test_mnemonic(self, client):
        debuglink.load_device_by_mnemonic(
            client,
            mnemonic=MNEMONIC12,
            pin="",
            passphrase_protection=False,
            label="test",
        )
        mnemonic = client.debug.state().mnemonic_secret
        assert mnemonic == MNEMONIC12.encode()

    @pytest.mark.setup_client(mnemonic=MNEMONIC12, pin="1234", passphrase=True)
    def test_pin(self, client):
        resp = client.call_raw(messages.Ping(message="test", pin_protection=True))
        assert isinstance(resp, messages.PinMatrixRequest)

        pin, matrix = client.debug.read_pin()
        assert pin == "1234"
        assert matrix != ""

        pin_encoded = client.debug.read_pin_encoded()
        resp = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))
        assert isinstance(resp, messages.Success)
