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
from .common import Menu

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, _label_choices
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler
# Trezor Safe 7 only
pytestmark = [pytest.mark.models("eckhart")]

KEYBOARD_CATEGORY = KeyboardCategory.LettersLower

LABEL10 = "NewLabel0#"
LABEL31 = "dadadadadadadadadadadadadadadad"
LABEL32 = LABEL31 + "a"
LABEL33 = LABEL32 + "d"

LABEL_TITLE = TR.words__name


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
    is_empty: bool = len(debug.read_layout().label()) == 0
    allow_empty = debug.read_layout().find_unique_value_by_key(
        "allow_empty", default=False, only_type=bool
    )

    if is_empty:
        assert allow_empty

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
    assert LABEL_TITLE in Menu.DEVICE.content(features)

    # Start at homescreen
    debug.synchronize_at("Homescreen")

    # Click on the device menu
    debug.click(debug.screen_buttons.ok())
    debug.synchronize_at("DeviceMenuScreen")

    # Navigate to device menu
    Menu.DEVICE.navigate_to(debug, features)

    # Trigger label change
    layout = debug.read_layout()
    label_idx = layout.vertical_menu_content().index(LABEL_TITLE)
    debug.button_actions.navigate_to_menu_item(label_idx)


@pytest.mark.setup_client(pin=None)
def test_change_label(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    label = features.label
    assert isinstance(label, str)

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)
    # Make sure the current label is prefilled
    assert debug.read_layout().label() == label
    # Erase the current label
    erase_label(debug)
    # Input new label
    input_label(debug, LABEL10)
    # Confirm label keyboard
    enter_label(debug)
    # Confirm label change
    confirm_label(debug)
    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")
    # Assert the correct label on the homescreen
    assert LABEL10 in debug.read_layout().text_content()
    # Open the device menu, it must not fail due to label button text overflow
    debug.click(debug.screen_buttons.ok())
    debug.synchronize_at("DeviceMenuScreen")
    # Navigate to device menu
    Menu.DEVICE.navigate_to(debug, features)
    # Check the correct label in the button subtext
    layout = debug.read_layout()
    label_idx = layout.vertical_menu_content().index(LABEL_TITLE)
    assert layout.vertical_menu_subtext()[label_idx] == LABEL10

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

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)
    # Erase the current label
    erase_label(debug)
    # Cancel button is available when the label is empty
    cancel_label(debug)
    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")

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
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    label = features.label
    assert isinstance(label, str)

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)
    # Erase the current label
    erase_label(debug)
    # Confirm empty label keyboard
    enter_label(debug)
    # Confirm label change
    confirm_label(debug)
    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label == ""


@pytest.mark.setup_client(pin=None)
def test_label_over_32_chars(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label is not None

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)

    # Erase the current label
    erase_label(debug)
    # Try to input label longer than 32 characters
    input_label(debug, LABEL33, check=False)
    # Assert that the label is truncated to 32 characters
    assert debug.read_layout().label() == LABEL32
    # Confirm label keyboard
    enter_label(debug)
    # Confirm label change
    confirm_label(debug)
    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")
    # Assert the correct label on the homescreen
    assert debug.read_layout().text_content() == LABEL32
    # Open the device menu, it must not fail due to label button text overflow
    # TODO allow when the menu can handle long labels
    # debug.click(debug.screen_buttons.ok())
    # debug.synchronize_at("DeviceMenuScreen")
    # # Navigate to device menu
    # Menu.DEVICE.navigate_to(debug, features)
    # # Check the correct label in the button subtext
    # layout = debug.read_layout()
    # label_idx = layout.vertical_menu_content().index(LABEL_TITLE)
    # assert layout.vertical_menu_subtext()[label_idx] == LABEL32

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

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)
    # Erase the current label
    erase_label(debug)
    # Loop through all keyboard categories
    for category in (
        KeyboardCategory.Numeric,
        KeyboardCategory.LettersLower,
        KeyboardCategory.LettersUpper,
        KeyboardCategory.Special,
    ):
        go_to_category(debug, category, True)
    debug.read_layout()
    # Cancel button is available when the label is empty
    cancel_label(debug)
    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")

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

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)
    # Erase the current label
    erase_label(debug)
    # Check that the button wrapping works

    # Test that button wrapping works properly
    count = 10
    letter = "a"
    a_coords, _ = debug.button_actions.label(letter)
    keys = debug.button_actions._label_choices(letter)
    key = next(group for group in keys if letter in group)
    for _ in range(count):
        debug.click(a_coords)
    assert debug.read_layout().label() == key[count % len(key) - 1]
    # Confirm label keyboard
    enter_label(debug)
    # Confirm label change
    confirm_label(debug)
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

    # Get to the Label change flow
    prepare_label_dialogue(debug, features)
    # Erase the current label
    erase_label(debug)
    # Label that cycles through "ghi" in the last character
    label = LABEL31 + "i"
    # Input new label
    input_label(debug, label)
    assert debug.read_layout().label() == label
    # Confirm label keyboard
    enter_label(debug)
    # Confirm label change
    confirm_label(debug)
    # Wait for the homescreen to appear
    debug.synchronize_at("Homescreen")

    features = device_handler.features()
    assert features.initialized is True
    assert features.pin_protection is False
    assert features.unfinished_backup is not True
    assert features.label == label
