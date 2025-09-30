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

from enum import Enum
from typing import TYPE_CHECKING

import pytest

from ... import translations as TR
from ..common import go_next
from ..test_pin import (
    PIN1,
    PIN4,
    _cancel_code,
    _delete_code,
    _enter_two_times,
    _input_code,
    _input_see_confirm,
    _see_code,
)
from .common import (
    Menu,
    NoSecuritySettings,
    assert_device_screen,
    close_device_menu,
    enter_pin,
    open_device_menu,
)

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]

PIN_TITLE = "pin__title"


class Situation(Enum):
    SETUP = 1
    CHANGE = 2
    REMOVE = 3


def prepare_pin_dialogue(
    debug: "DebugLink", features: "Features", situation: Situation
) -> None:
    pin_title = TR.translate(PIN_TITLE)
    security_content = Menu.SECURITY.content(features)
    if security_content is None:
        raise NoSecuritySettings

    assert pin_title in security_content

    # Open device menu
    open_device_menu(debug)

    if situation is Situation.SETUP:
        assert features.pin_protection is False
        # Pin submenu shouldn't be present
        assert Menu.PIN.content(features) is None
        # Navigate to security menu
        Menu.SECURITY.navigate_to(debug, features)

        title = TR.translate(PIN_TITLE)
    else:
        assert features.pin_protection is True
        # Navigate to pin menu
        Menu.PIN.navigate_to(debug, features)

        if situation is Situation.CHANGE:
            title = TR.pin__change
        elif situation is Situation.REMOVE:
            title = TR.pin__remove
        else:
            raise RuntimeError("Unknown situation")

    # Trigger pin action
    layout = debug.read_layout()
    pin_idx = layout.vertical_menu_content().index(title)
    debug.button_actions.navigate_to_menu_item(pin_idx)


@pytest.mark.setup_client(uninitialized=True)
def test_pin_uninitialized(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()

    # Device is uninitialized, the entire security menu is not accessible
    with pytest.raises(NoSecuritySettings):
        prepare_pin_dialogue(debug, features, Situation.SETUP)


@pytest.mark.setup_client(pin=None)
def test_pin_setup(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()

    prepare_pin_dialogue(debug, features, Situation.SETUP)

    # Intro screen
    go_next(debug)
    # Enter pin twice
    _enter_two_times(debug, PIN4, PIN4)
    # Confirmation screen
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is True


@pytest.mark.setup_client(pin=None)
def test_pin_cancel_intro(device_handler: "BackgroundDeviceHandler"):

    debug = device_handler.debuglink()
    features = device_handler.features()

    prepare_pin_dialogue(debug, features, Situation.SETUP)

    # Go to menu in the intro screen
    debug.click(debug.screen_buttons.menu())
    # Press cancel
    debug.button_actions.navigate_to_menu_item(0)
    # Confirm cancel
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is False


@pytest.mark.setup_client(pin=None)
def test_pin_cancel_keyboard(device_handler: "BackgroundDeviceHandler"):

    debug = device_handler.debuglink()
    features = device_handler.features()

    prepare_pin_dialogue(debug, features, Situation.SETUP)

    # Intro screen
    go_next(debug)
    # Enter PIN, then cancel
    _input_code(debug, PIN1)
    _see_code(debug)
    _delete_code(debug, len(PIN1))
    _see_code(debug)
    _cancel_code(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_pin_change(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.pin_protection is True
    prepare_pin_dialogue(debug, features, Situation.CHANGE)

    # Intro screen
    go_next(debug)
    # Input old pin to authorize
    _input_see_confirm(debug, PIN4)
    # Input new pin 2 times
    _enter_two_times(debug, PIN1, PIN1)
    # Confirmation screen
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is True


@pytest.mark.setup_client(pin=PIN4)
def test_pin_remove(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()

    prepare_pin_dialogue(debug, features, Situation.REMOVE)

    # Intro screen
    go_next(debug)
    # Enter pin to remove
    _input_see_confirm(debug, PIN4)
    # Confirmation screen
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is False
