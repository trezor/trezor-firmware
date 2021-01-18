# This file is part of the Trezor project.
#
# Copyright (C) 2012-2021 SatoshiLabs and contributors
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

from .. import buttons, common

PIN4 = "1234"


@pytest.mark.setup_client(pin=PIN4)
def test_hold_to_lock(device_handler):
    debug = device_handler.debuglink()

    def hold(duration, wait=True):
        debug.input(x=13, y=37, hold_ms=duration, wait=wait)
        time.sleep(duration / 1000 + 0.5)

    assert device_handler.features().unlocked is False

    # unlock with message
    device_handler.run(common.get_test_address)
    layout = debug.wait_layout()
    assert layout.text == "PinDialog"
    debug.input("1234", wait=True)
    assert device_handler.result()

    assert device_handler.features().unlocked is True

    # short touch
    hold(1000, wait=False)
    assert device_handler.features().unlocked is True

    # lock
    hold(3500)
    assert device_handler.features().unlocked is False

    # unlock by touching
    layout = debug.click(buttons.INFO, wait=True)
    assert layout.text == "PinDialog"
    debug.input("1234", wait=True)

    assert device_handler.features().unlocked is True

    # lock
    hold(3500)
    assert device_handler.features().unlocked is False
