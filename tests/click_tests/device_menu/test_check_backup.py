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
from ...common import MNEMONIC12
from .common import (
    Menu,
    MenuItemNotFound,
    NoSecuritySettings,
    assert_device_screen,
    close_device_menu,
    open_device_menu,
)

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]


def prepare_check_backup(debug: "DebugLink", features: "Features") -> None:
    check_backup_title = TR.reset__check_backup_title
    security_content = Menu.SECURITY.content(features)
    if security_content is None:
        raise NoSecuritySettings

    if check_backup_title not in Menu.SECURITY.content(features):
        raise MenuItemNotFound(check_backup_title)

    # Open device menu
    open_device_menu(debug)

    # Navigate to device menu
    Menu.SECURITY.navigate_to(debug, features)

    # Trigger check backup
    layout = debug.read_layout()
    label_idx = layout.vertical_menu_content().index(check_backup_title)
    debug.button_actions.navigate_to_menu_item(label_idx)


@pytest.mark.setup_client(uninitialized=True)
def test_uninitialized_fails(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is False
    assert features.pin_protection is False
    assert features.unfinished_backup is False

    # Device is uninitialized, security settings are not accessible in the settings
    with pytest.raises(NoSecuritySettings):
        prepare_check_backup(debug, features)


@pytest.mark.setup_client(needs_backup=True)
def test_backup_needed_fails(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.backup_availability == messages.BackupAvailability.Required

    # Device needs backup, check backup is not accessible in the security settings
    with pytest.raises(MenuItemNotFound, match=TR.reset__check_backup_title):
        prepare_check_backup(debug, features)


@pytest.mark.setup_client(no_backup=True)
def test_no_backup_fails(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.no_backup is True

    # Device has no backup, check backup is not accessible in the security settings
    with pytest.raises(MenuItemNotFound, match=TR.reset__check_backup_title):
        prepare_check_backup(debug, features)


@pytest.mark.setup_client(pin=None, mnemonic=MNEMONIC12)
def test_backup_check_cancel(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.backup_availability is messages.BackupAvailability.NotAvailable

    # Start check backup flow
    prepare_check_backup(debug, features)
    assert TR.recovery__check_dry_run in debug.read_layout().text_content()

    # Cancel the flow
    debug.click(debug.screen_buttons.cancel())
    assert_device_screen(debug, Menu.SECURITY)

    close_device_menu(debug)
