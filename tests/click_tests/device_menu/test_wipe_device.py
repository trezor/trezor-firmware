# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING

import pytest

from ... import translations as TR
from .common import PIN4, Menu, enter_pin, open_device_menu

if TYPE_CHECKING:
    from ...device_handler import BackgroundDeviceHandler

# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]


@pytest.mark.invalidate_client
@pytest.mark.setup_client(pin=PIN4)
def test_wipe(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True

    wipe_title = TR.wipe__title
    assert wipe_title in Menu.DEVICE.content(features)

    open_device_menu(debug)

    # Navigate to device menu
    Menu.DEVICE.navigate_to(debug, features)

    # Trigger wipe
    layout = debug.read_layout()
    wipe_idx = layout.vertical_menu_content().index(wipe_title)
    debug.button_actions.navigate_to_menu_item(wipe_idx)

    # Confirm wipe
    debug.synchronize_at(wipe_title)
    debug.click(debug.screen_buttons.ok())

    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")

    device_handler.client = device_handler.client.get_new_client()
    features = device_handler.features()
    assert features.initialized is False
    assert features.pin_protection is False
