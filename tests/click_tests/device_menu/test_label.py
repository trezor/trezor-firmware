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
from ..common import KeyboardCategory, delete_char, go_to_category, press_char
from .common import Menu, assert_device_screen, close_device_menu, open_device_menu

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]

KEYBOARD_CATEGORY = KeyboardCategory.LettersLower

LABEL10 = "NewLabel0#"
LABEL31 = "dadadadadadadadadadadadadadadad"
LABEL32 = LABEL31 + "a"
LABEL33 = LABEL32 + "d"


def input_label(debug: "DebugLink", label: str, check: bool = True) -> None:
    """Input a label with validation it got added"""
    if check:
        before = debug.read_layout().label()
    for char in label:
        press_char(debug, char)
    if check:
        after = debug.read_layout().label()
        assert after == before + label


def enter_label(debug: "DebugLink") -> None:
    """Enter a label"""
    debug.click(debug.screen_buttons.passphrase_confirm())


def confirm_label(debug: "DebugLink") -> None:
    """Apply label setting"""
    # Confirm label change
    debug.synchronize_at(TR.device_name__title)
    debug.click(debug.screen_buttons.ok())


def erase_label(debug: "DebugLink", check: bool = True) -> None:
    """Erase a label with validation it got erased"""
    # Erase the current label
    for _ in range(len(debug.read_layout().label())):
        delete_char(debug)
    if check:
        assert debug.read_layout().label() == ""


def cancel_label(debug: "DebugLink") -> None:
    """Cancel label input"""
    debug.click(debug.screen_buttons.pin_passphrase_erase())


def prepare_label_dialogue(debug: "DebugLink", features: "Features") -> None:
    label_title = TR.words__name
    assert label_title in Menu.DEVICE.content(features)

    # Open device menu
    open_device_menu(debug)

    # Navigate to device menu
    Menu.DEVICE.navigate_to(debug, features)

    # Trigger label change
    layout = debug.read_layout()
    label_idx = layout.vertical_menu_content().index(label_title)
    debug.button_actions.navigate_to_menu_item(label_idx)


@pytest.mark.setup_client(uninitialized=True)
def test_label_uninitialized(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    features = device_handler.features()
    assert features.initialized is False
    assert features.pin_protection is False
    assert features.unfinished_backup is False

    # device is uninitialized, device name is not accessible in the device menu
    with pytest.raises(AssertionError, match=f"'{TR.words__name}' in"):
        prepare_label_dialogue(debug, features)


@pytest.mark.setup_client(pin=None)
def test_change_label(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    label = features.label
    assert isinstance(label, str)

    prepare_label_dialogue(debug, features)

    assert debug.read_layout().label() == label

    # Input new label
    erase_label(debug)
    input_label(debug, LABEL10)
    enter_label(debug)
    confirm_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label == LABEL10


@pytest.mark.setup_client(pin=None)
def test_label_cancel(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    label = features.label
    assert isinstance(label, str)

    prepare_label_dialogue(debug, features)

    erase_label(debug)
    cancel_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label == label


@pytest.mark.setup_client(pin=None)
def test_label_empty(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True

    prepare_label_dialogue(debug, features)

    erase_label(debug)
    enter_label(debug)
    confirm_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)

    # Make sure the label is empty
    features = device_handler.features()
    assert features.initialized is True
    assert features.label == ""

    # When the label is empty, the homescreen shows the model name
    assert debug.read_layout().screen_content() == "Trezor Safe 7"


@pytest.mark.setup_client(pin=None)
def test_label_over_32_chars(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None

    prepare_label_dialogue(debug, features)

    # Input new label
    erase_label(debug)
    input_label(debug, LABEL33, check=False)
    assert debug.read_layout().label() == LABEL32
    enter_label(debug)
    confirm_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label == LABEL32


@pytest.mark.setup_client(pin=None)
def test_label_loop_all_categories(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None

    prepare_label_dialogue(debug, features)

    # Input new label
    erase_label(debug)

    for category in (
        KeyboardCategory.Numeric,
        KeyboardCategory.LettersLower,
        KeyboardCategory.LettersUpper,
        KeyboardCategory.Special,
    ):
        go_to_category(debug, category, True)

    debug.read_layout()
    cancel_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None


@pytest.mark.setup_client(pin=None)
def test_label_click_same_button_many_times(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None

    prepare_label_dialogue(debug, features)

    # Input new label
    erase_label(debug)

    a_coords, _ = debug.button_actions.label("a")
    for _ in range(10):
        debug.click(a_coords)

    enter_label(debug)
    confirm_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    # Close the device menu
    debug.synchronize_at("DeviceMenuScreen")
    debug.click(debug.screen_buttons.menu())

    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None


@pytest.mark.setup_client(pin=None)
def test_label_cycle_through_last_character(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None

    prepare_label_dialogue(debug, features)

    # Input new label
    erase_label(debug)

    label = LABEL31 + "i"  # for i we need to cycle through "ghi" three times
    input_label(debug, label)
    assert debug.read_layout().label() == label
    enter_label(debug)
    confirm_label(debug)
    assert_device_screen(debug, Menu.DEVICE)

    close_device_menu(debug)
    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label == label
