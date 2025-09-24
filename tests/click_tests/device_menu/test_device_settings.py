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
from .common import Menu, assert_device_screen, close_device_menu, open_device_menu

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]

LED_TITLE = "led__title"
BRIGHTNESS_TITLE = "brightness__title"
HAPTIC_FEEDBACK_TITLE = "haptic_feedback__title"


def prepare_device_menu(debug: "DebugLink", features: "Features") -> None:
    """Navigate to the device settings menu"""

    # Open device menu
    open_device_menu(debug)

    # Navigate to device menu
    Menu.DEVICE.navigate_to(debug, features)


@pytest.mark.setup_client(uninitialized=True)
def test_device_settings_uninitialized(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is False
    assert features.pin_protection is False

    prepare_device_menu(debug, features)

    items = debug.read_layout().vertical_menu_content()

    assert TR.translate(LED_TITLE) not in items
    assert TR.translate(BRIGHTNESS_TITLE) not in items
    assert TR.translate(HAPTIC_FEEDBACK_TITLE) not in items


@pytest.mark.setup_client(pin=None)
def test_toggle_led(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False

    # make sure the device has LED
    assert features.led is not None

    # Go to device settings
    prepare_device_menu(debug, features)

    # Toggle LED setting
    items = debug.read_layout().vertical_menu_content()
    assert TR.translate(LED_TITLE) in items
    led_idx = items.index(TR.translate(LED_TITLE))
    led_old = features.led
    debug.button_actions.navigate_to_menu_item(led_idx)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)

    # Refresh features
    features = device_handler.features()
    led_new = features.led
    assert led_new is not None
    # Make sure the LED setting was toggled
    assert led_new != led_old


@pytest.mark.setup_client(pin=None)
def test_toggle_haptic(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()

    if features.haptic_feedback is None:
        pytest.skip("haptic feedback not supported")

    assert features.initialized is True
    assert features.pin_protection is False

    # Go to device settings
    prepare_device_menu(debug, features)

    # Toggle haptic setting
    items = debug.read_layout().vertical_menu_content()
    assert TR.translate(HAPTIC_FEEDBACK_TITLE) in items
    haptic_idx = items.index(TR.translate(HAPTIC_FEEDBACK_TITLE))
    haptic_old = features.haptic_feedback
    debug.button_actions.navigate_to_menu_item(haptic_idx)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)

    # Refresh features
    features = device_handler.features()
    haptic_new = features.haptic_feedback
    assert haptic_new is not None
    # Make sure the haptic setting was toggled
    assert haptic_new != haptic_old


@pytest.mark.setup_client(pin=None)
def test_brightness(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True

    # Go to device settings
    prepare_device_menu(debug, features)

    # Go to brightness setting
    items = debug.read_layout().vertical_menu_content()
    assert TR.translate(BRIGHTNESS_TITLE) in items
    brightness_idx = items.index(TR.translate(BRIGHTNESS_TITLE))
    debug.button_actions.navigate_to_menu_item(brightness_idx)
    debug.synchronize_at("SetBrightnessScreen")

    # Close brightness setting
    debug.click(debug.screen_buttons.menu())

    # Make sure we are back at the device settings menu
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)
