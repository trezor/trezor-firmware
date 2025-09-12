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

from .common import PIN4, Menu, enter_pin

if TYPE_CHECKING:
    from ...device_handler import BackgroundDeviceHandler

# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]


@pytest.mark.setup_client(pin=PIN4)
def test_traverse_initialized(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True
    assert features.unfinished_backup is not True

    # Start at homescreen
    debug.synchronize_at("Homescreen")

    # Click on the device menu
    debug.click(debug.screen_buttons.ok())
    debug.synchronize_at("DeviceMenuScreen")

    Menu.traverse(debug, features)

    # Close the device menu
    debug.click(debug.screen_buttons.menu())

    # End at homescreen
    debug.synchronize_at("Homescreen")


@pytest.mark.setup_client(pin=None)
def test_traverse_initialized_no_pin(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True

    # Start at homescreen
    debug.synchronize_at("Homescreen")

    # Click on the device menu
    debug.click(debug.screen_buttons.ok())
    debug.synchronize_at("DeviceMenuScreen")

    Menu.traverse(debug, features)

    # Close the device menu
    debug.click(debug.screen_buttons.menu())

    # End at homescreen
    debug.synchronize_at("Homescreen")


@pytest.mark.setup_client(uninitialized=True)
def test_traverse_uninitialized(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is False
    assert features.pin_protection is False
    assert features.unfinished_backup is False

    # Start at homescreen
    debug.synchronize_at("Homescreen")

    # Click on the device menu
    debug.click(debug.screen_buttons.ok())
    debug.synchronize_at("DeviceMenuScreen")

    Menu.traverse(debug, features)

    # Close the device menu
    debug.click(debug.screen_buttons.menu())

    # End at homescreen
    debug.synchronize_at("Homescreen")
