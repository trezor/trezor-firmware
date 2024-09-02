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
from typing import TYPE_CHECKING

import pytest

from trezorlib import models
from trezorlib.debuglink import LayoutType

from .. import buttons, common

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


PIN4 = "1234"


@pytest.mark.setup_client(pin=PIN4)
def test_hold_to_lock(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    short_duration = {
        models.T1B1: 500,
        models.T2B1: 500,
        models.T3B1: 500,
        models.T2T1: 1000,
        models.T3T1: 1000,
    }[debug.model]
    lock_duration = {
        models.T1B1: 1200,
        models.T2B1: 1200,
        models.T3B1: 1200,
        models.T2T1: 3500,
        models.T3T1: 3500,
    }[debug.model]

    def hold(duration: int, wait: bool = True) -> None:
        if debug.layout_type is LayoutType.TR:
            debug.press_right_htc(hold_ms=duration)
        else:
            debug.input(x=13, y=37, hold_ms=duration, wait=wait)

    assert device_handler.features().unlocked is False

    # unlock with message
    device_handler.run(common.get_test_address)

    assert "PinKeyboard" in debug.wait_layout().all_components()
    debug.input("1234", wait=True)
    assert device_handler.result()

    assert device_handler.features().unlocked is True

    # short touch
    hold(short_duration)

    time.sleep(0.5)  # so that the homescreen appears again (hacky)
    assert device_handler.features().unlocked is True

    # lock
    hold(lock_duration)
    assert device_handler.features().unlocked is False

    # unlock by touching
    if debug.layout_type is LayoutType.TR:
        # Doing a short HTC to simulate a click
        debug.press_right_htc(hold_ms=100)
        layout = debug.wait_layout()
    else:
        layout = debug.click(buttons.INFO, wait=True)
    assert "PinKeyboard" in layout.all_components()
    debug.input("1234", wait=True)

    assert device_handler.features().unlocked is True

    # lock
    hold(lock_duration)
    assert device_handler.features().unlocked is False
