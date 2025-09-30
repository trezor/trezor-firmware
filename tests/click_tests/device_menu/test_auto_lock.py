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
from ..test_pin import PIN4
from .common import (
    Menu,
    MenuItemNotFound,
    assert_device_screen,
    close_device_menu,
    enter_pin,
    format_duration_ms,
    open_device_menu,
)

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]


BATTERY_AUTO_LOCK_IDX = 0
USB_AUTO_LOCK_IDX = 1


def prepare_auto_lock(debug: "DebugLink", features: "Features") -> None:
    """Navigate to the auto-lock settings dialogue"""

    # Open device menu
    open_device_menu(debug)

    # Navigate to device menu
    Menu.AUTO_LOCK.navigate_to(debug, features)


@pytest.mark.setup_client(uninitialized=True)
def test_auto_lock_uninitialized(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is False
    assert features.pin_protection is False

    # device is uninitialized, security menu is not accessible
    with pytest.raises(MenuItemNotFound, match=TR.words__security):
        prepare_auto_lock(debug, features)


@pytest.mark.setup_client(pin=None)
def test_auto_lock_pin_not_set(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False

    # device is uninitialized, auto-lock menu is not accessible
    with pytest.raises(MenuItemNotFound, match=TR.auto_lock__title):
        prepare_auto_lock(debug, features)


@pytest.mark.setup_client(pin=PIN4)
def test_auto_lock_battery_change(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True
    # auto-lock is not set by default
    assert features.auto_lock_delay_battery_ms is None

    enter_pin(device_handler)
    debug = device_handler.debuglink()

    prepare_auto_lock(debug, features)

    # Battery auto-lock
    debug.button_actions.navigate_to_menu_item(0)
    # Decrease value by one step
    debug.click(debug.screen_buttons.number_input_minus())
    # Confirm value
    debug.click(debug.screen_buttons.ok())
    # Confirm changes
    debug.click(debug.screen_buttons.ok())
    # Make sure we are back at the security menu and go to homescreen
    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    # Refresh features
    features = device_handler.features()
    # Make sure auto-lock is set
    assert features.auto_lock_delay_ms is not None

    # Verify the changes are reflected in the menu
    prepare_auto_lock(debug, features)
    auto_lock_items = debug.read_layout().vertical_menu_content()
    assert format_duration_ms(features.auto_lock_delay_ms) == auto_lock_items[1]
    close_device_menu(debug)


@pytest.mark.setup_client(pin=PIN4)
def test_auto_lock_usb_change(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True
    # auto-lock is not set by default
    assert features.auto_lock_delay_ms is None

    enter_pin(device_handler)
    debug = device_handler.debuglink()

    prepare_auto_lock(debug, features)

    # USB auto-lock
    debug.button_actions.navigate_to_menu_item(1)
    # Increase value by one step
    debug.click(debug.screen_buttons.number_input_plus())
    # Confirm value
    debug.click(debug.screen_buttons.ok())
    # Confirm changes
    debug.click(debug.screen_buttons.ok())
    # Make sure we are back at the security menu and go to homescreen
    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    # Refresh features
    features = device_handler.features()
    # Make sure auto-lock is set
    assert features.auto_lock_delay_ms is not None

    # Verify the changes are reflected in the menu
    prepare_auto_lock(debug, features)
    auto_lock_items = debug.read_layout().vertical_menu_content()
    assert format_duration_ms(features.auto_lock_delay_ms) == auto_lock_items[1]
    close_device_menu(debug)


@pytest.mark.setup_client(pin=PIN4)
def test_auto_lock_battery_cancel(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True
    # auto-lock is not set by default
    assert features.auto_lock_delay_battery_ms is None

    enter_pin(device_handler)
    debug = device_handler.debuglink()

    prepare_auto_lock(debug, features)

    # Battery auto-lock
    old_items = debug.read_layout().vertical_menu_content()
    debug.button_actions.navigate_to_menu_item(BATTERY_AUTO_LOCK_IDX)
    # Increase value by one step
    debug.click(debug.screen_buttons.number_input_plus())
    # Cancel auto-lock change
    debug.click(debug.screen_buttons.cancel())
    # Make sure we are back at the security menu and go to homescreen
    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    # Refresh features
    features = device_handler.features()

    # Verify there are no changes
    prepare_auto_lock(debug, features)
    items = debug.read_layout().vertical_menu_content()
    assert old_items[BATTERY_AUTO_LOCK_IDX] == items[BATTERY_AUTO_LOCK_IDX]
    close_device_menu(debug)


@pytest.mark.setup_client(pin=PIN4)
def test_auto_lock_usb_cancel(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True
    # auto-lock is not set by default
    assert features.auto_lock_delay_ms is None

    enter_pin(device_handler)
    debug = device_handler.debuglink()

    prepare_auto_lock(debug, features)

    # USB auto-lock
    old_items = debug.read_layout().vertical_menu_content()
    debug.button_actions.navigate_to_menu_item(USB_AUTO_LOCK_IDX)
    # Increase value by one step
    debug.click(debug.screen_buttons.number_input_plus())
    # Cancel auto-lock change
    debug.click(debug.screen_buttons.cancel())
    # Make sure we are back at the security menu and go to homescreen
    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    # Refresh features
    features = device_handler.features()

    # Verify there are no changes
    prepare_auto_lock(debug, features)
    items = debug.read_layout().vertical_menu_content()
    assert old_items[USB_AUTO_LOCK_IDX] == items[USB_AUTO_LOCK_IDX]
    close_device_menu(debug)
