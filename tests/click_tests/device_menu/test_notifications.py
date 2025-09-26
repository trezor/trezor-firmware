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

from trezorlib import messages

from ... import translations as TR
from ..test_pin import PIN4, _assert_pin_entry, _enter_two_times
from .common import Menu, assert_device_screen, close_device_menu, open_device_menu

if TYPE_CHECKING:

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]


@pytest.mark.setup_client(pin=None)
def test_pin_not_set(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is False

    # Open device menu
    open_device_menu(debug)

    # Click on the "PIN not set" notification
    pin_notification = TR.homescreen__title_pin_not_set
    layout = debug.read_layout()
    pin_notification_idx = layout.vertical_menu_content().index(pin_notification)
    debug.button_actions.navigate_to_menu_item(pin_notification_idx)

    # 1st screen of the pin set flow
    assert debug.read_layout().text_content() == TR.pin__info
    debug.click(debug.screen_buttons.ok())

    # set new pin
    _assert_pin_entry(debug)
    _enter_two_times(debug, PIN4, PIN4)

    # Close the flow
    debug.click(debug.screen_buttons.ok())
    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is True


@pytest.mark.setup_client(needs_backup=True, pin=None)
def test_backup_needed(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.backup_availability is messages.BackupAvailability.Required
    assert features.unfinished_backup is False
    assert features.pin_protection is False

    # Open device menu
    open_device_menu(debug)

    backup_notification = TR.homescreen__title_backup_needed
    pin_notification = TR.homescreen__title_pin_not_set
    layout = debug.read_layout()
    pin_notification_idx = layout.vertical_menu_content().index(pin_notification)
    backup_notification_idx = layout.vertical_menu_content().index(backup_notification)

    # Make sure the "Backup needed" notification is above the "PIN not set" notification
    assert backup_notification_idx < pin_notification_idx

    # Go to the "Backup needed" info screen
    debug.button_actions.navigate_to_menu_item(backup_notification_idx)
    assert TR.homescreen__backup_needed_info in debug.read_layout().text_content()

    # Close the screen
    debug.click(debug.screen_buttons.menu())
    assert_device_screen(debug, Menu.ROOT)
    close_device_menu(debug)


@pytest.mark.setup_client(no_backup=True)
def test_seedless(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is True
    assert features.no_backup is True
    assert features.unfinished_backup is False

    # Open device menu
    open_device_menu(debug)

    backup_notification = TR.homescreen__title_backup_needed
    layout = debug.read_layout()

    # No "Backup needed" notification should be present
    with pytest.raises(ValueError, match=f"'{backup_notification}' is not in"):
        layout.vertical_menu_content().index(backup_notification)
