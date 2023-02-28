# This file is part of the Trezor project.
#
# Copyright (C) 2022 SatoshiLabs and contributors
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

import time

import pytest

from trezorlib import btc, device
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

PIN = "1234"


@pytest.mark.setup_client(pin=PIN)
def test_busy_state(client: Client):
    assert client.features.unlocked is False
    assert client.features.busy is False

    # Show busy dialog for 1 minute.
    device.set_busy(client, expiry_ms=60 * 1000)
    assert client.features.unlocked is False
    assert client.features.busy is True

    with client:
        client.use_pin_sequence([PIN])
        btc.get_address(
            client, "Bitcoin", parse_path("m/44h/0h/0h/0/0"), show_display=True
        )

    client.refresh_features()
    assert client.features.unlocked is True
    assert client.features.busy is True

    # Hide the busy dialog.
    device.set_busy(client, None)

    assert client.features.unlocked is True
    assert client.features.busy is False


def test_busy_expiry(client: Client):
    expiry_ms = 100  # 100 milliseconds

    # Show the busy dialog.
    device.set_busy(client, expiry_ms=expiry_ms)

    # Wait for it to expire.
    time.sleep(expiry_ms / 1000)

    # Check that the device is no longer busy.
    client.refresh_features()
    assert client.features.busy is False
