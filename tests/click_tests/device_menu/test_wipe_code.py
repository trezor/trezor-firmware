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
    MenuItemNotFound,
    assert_device_screen,
    close_device_menu,
    enter_pin,
    open_device_menu,
)
from .test_pin import Situation, prepare_pin_dialogue

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]

WIPE_CODE = "2"
WIPE_CODE_TITLE = "wipe_code__title"


def change_wipe_code(
    debug: "DebugLink", pin: str = PIN4, wipe_code: str = WIPE_CODE
) -> None:
    # Intro screen
    go_next(debug)
    # Enter pin to authorize
    _input_see_confirm(debug, pin)
    # Enter new wipe code twice
    _enter_two_times(debug, wipe_code, wipe_code)
    # Confirmation screen
    go_next(debug)


def prepare_wipe_dialogue(
    device_handler: "BackgroundDeviceHandler", situation: Situation
) -> None:

    debug = device_handler.debuglink()
    features = device_handler.features()
    wipe_title = TR.translate(WIPE_CODE_TITLE)
    if wipe_title not in Menu.SECURITY.content(features):
        raise MenuItemNotFound(wipe_title)

    if situation in (Situation.REMOVE, Situation.CHANGE):
        assert features.wipe_code_protection is False
        open_device_menu(debug)
        Menu.SECURITY.navigate_to(debug, features)
        layout = debug.read_layout()
        idx = layout.vertical_menu_content().index(TR.translate(WIPE_CODE_TITLE))
        debug.button_actions.navigate_to_menu_item(idx)

        change_wipe_code(debug)

        assert_device_screen(debug, Menu.SECURITY)
        close_device_menu(debug)

        features = device_handler.features()
        assert features.wipe_code_protection is True

    # Open device menu
    open_device_menu(debug)

    assert features.pin_protection is True

    if situation is Situation.SETUP:
        assert features.wipe_code_protection is False
        # Wipe code submenu shouldn't be present
        assert Menu.WIPE_CODE.content(features) is None
        # Navigate to security menu
        Menu.SECURITY.navigate_to(debug, features)
        title = TR.translate(WIPE_CODE_TITLE)
    else:
        assert features.wipe_code_protection is True
        # Navigate to wipe code menu
        Menu.WIPE_CODE.navigate_to(debug, features)

        if situation is Situation.CHANGE:
            title = TR.wipe_code__change

        elif situation is Situation.REMOVE:
            title = TR.wipe_code__remove
        else:
            raise RuntimeError("Unknown situation")

    # Trigger wipe code dialogue
    layout = debug.read_layout()
    idx = layout.vertical_menu_content().index(title)
    debug.button_actions.navigate_to_menu_item(idx)


@pytest.mark.setup_client(pin=None)
def test_wipe_code_setup_pin_unset(device_handler: "BackgroundDeviceHandler"):

    # Device doesn't have the pin set, the wipe code button is not accessible
    with pytest.raises(
        MenuItemNotFound,
        match=TR.translate("wipe_code__title"),
    ):
        prepare_wipe_dialogue(device_handler, Situation.SETUP)


@pytest.mark.setup_client(pin=PIN4)
def test_wipe_code_setup(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.wipe_code_protection is False

    prepare_wipe_dialogue(device_handler, Situation.SETUP)

    change_wipe_code(debug, wipe_code=WIPE_CODE)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.wipe_code_protection is True


@pytest.mark.setup_client(pin=PIN4)
def test_wipe_code_same_as_pin(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    prepare_wipe_dialogue(device_handler, Situation.SETUP)

    # Intro screen
    go_next(debug)
    # Enter pin to authorize
    _input_see_confirm(debug, PIN4)
    # Input wipe code same as pin
    _input_see_confirm(debug, PIN4)
    # Try again
    go_next(debug)
    _enter_two_times(debug, WIPE_CODE, WIPE_CODE)
    # Confirmation screen
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.wipe_code_protection is True


@pytest.mark.setup_client(pin=PIN4)
def test_wipe_code_cancel_intro(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.wipe_code_protection is False

    prepare_wipe_dialogue(device_handler, Situation.SETUP)

    # Go to menu in the intro screen
    debug.click(debug.screen_buttons.menu())
    # Press cancel
    debug.button_actions.navigate_to_menu_item(0)
    # Confirm cancel
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_wipe_code_cancel_keyboard(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.wipe_code_protection is False

    prepare_wipe_dialogue(device_handler, Situation.SETUP)

    # Intro screen
    go_next(debug)
    # Enter pin to authorize
    _input_see_confirm(debug, PIN4)
    # Enter wipe code, then cancel
    _input_code(debug, PIN1)
    _see_code(debug)
    _delete_code(debug, len(PIN1))
    _see_code(debug)
    _cancel_code(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_wipe_code_change(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()

    prepare_wipe_dialogue(device_handler, Situation.CHANGE)

    change_wipe_code(debug, wipe_code="3")

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.wipe_code_protection is True


@pytest.mark.setup_client(pin=PIN4)
def test_wipe_code_remove(device_handler: "BackgroundDeviceHandler"):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()

    prepare_wipe_dialogue(device_handler, Situation.REMOVE)

    # Intro screen
    go_next(debug)
    # Enter pin to authorize
    _input_see_confirm(debug, PIN4)
    # Confirm removal
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_remove_pin_without_removing_wipe_code(
    device_handler: "BackgroundDeviceHandler",
):
    enter_pin(device_handler)

    debug = device_handler.debuglink()
    features = device_handler.features()

    # Setup wipe code first
    open_device_menu(debug)
    Menu.SECURITY.navigate_to(debug, features)
    layout = debug.read_layout()
    idx = layout.vertical_menu_content().index(TR.translate(WIPE_CODE_TITLE))
    debug.button_actions.navigate_to_menu_item(idx)
    change_wipe_code(debug)
    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is True
    assert features.wipe_code_protection is True

    # Remove pin
    prepare_pin_dialogue(debug, features, Situation.REMOVE)

    # Intro screen
    go_next(debug)

    # Warning about existing wipe code
    assert TR.pin__wipe_code_exists_description in debug.read_layout().text_content()
    go_next(debug)

    assert_device_screen(debug, Menu.SECURITY)
    close_device_menu(debug)

    features = device_handler.features()
    assert features.pin_protection is True
    assert features.wipe_code_protection is True
