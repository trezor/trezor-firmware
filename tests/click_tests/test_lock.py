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

from trezorlib import messages, models
from trezorlib.debuglink import LayoutType

from .. import buttons, common

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


PIN4 = "1234"


@pytest.mark.setup_client(pin=PIN4)
def test_hold_to_lock(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    session = device_handler.client.get_seedless_session()
    session.call(messages.LockDevice())
    session.refresh_features()

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

    def hold(duration: int) -> None:
        if debug.layout_type is LayoutType.Caesar:
            debug.press_right(hold_ms=duration)
        else:
            debug.click((13, 37), hold_ms=duration)

    assert device_handler.features().unlocked is False

    # unlock with message
    device_handler.run_with_session(common.get_test_address)

    assert "PinKeyboard" in debug.read_layout().all_components()
    debug.input("1234")
    assert device_handler.result()

    session.refresh_features()
    assert device_handler.features().unlocked is True

    # short touch
    hold(short_duration)

    time.sleep(0.5)  # so that the homescreen appears again (hacky)
    session.refresh_features()
    assert device_handler.features().unlocked is True

    # lock
    hold(lock_duration)
    session.refresh_features()
    assert device_handler.features().unlocked is False

    # unlock by touching
    if debug.layout_type is LayoutType.Caesar:
        debug.press_right()
    else:
        debug.click(buttons.INFO)
    layout = debug.read_layout()
    assert "PinKeyboard" in layout.all_components()
    debug.input("1234")

    session.refresh_features()
    assert device_handler.features().unlocked is True

    # lock
    hold(lock_duration)
    session.refresh_features()
    assert device_handler.features().unlocked is False
