# This file is part of the Trezor project.
#
# Copyright (C) 2012-2023 SatoshiLabs and contributors
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

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator, Optional, Tuple

import pytest

from trezorlib import exceptions

from .. import buttons
from ..common import get_test_address
from .common import CommonPass, PassphraseCategory, get_char_category

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("delizia")

PASSPHRASE_CANCELLED = pytest.raises(exceptions.Cancelled, match="")

KEYBOARD_CATEGORIES = [
    PassphraseCategory.LOWERCASE,
    PassphraseCategory.UPPERCASE,
    PassphraseCategory.DIGITS,
    PassphraseCategory.SPECIAL,
]

# fmt: off
PASSPHRASE_LOWERCASE = ("abc", "def", "ghi", "jkl", "mno", "pq", "rst", "uvw", "xyz", " *#")
PASSPHRASE_UPPERCASE = ("ABC", "DEF", "GHI", "JKL", "MNO", "PQ", "RST", "UVW", "XYZ", " *#")
PASSPHRASE_DIGITS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
PASSPHRASE_SPECIAL = ("_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^=")
# fmt: on

# TODO: better read this from the trace
KEYBOARD_CATEGORY = PassphraseCategory.LOWERCASE
COORDS_PREV: buttons.Coords = (0, 0)

# Testing the maximum length is really 50

DA_50 = 25 * "da"
DA_50_ADDRESS = "mg5L2i8HZKUvceK1sfmGHhE4gichFSsdvm"
assert len(DA_50) == 50

DA_49 = DA_50[:-1]
DA_49_ADDRESS = "mxrB75ydMS3ZzqmYKK28fj4bNMEx7dDw6e"
assert len(DA_49) == 49
assert DA_49_ADDRESS != DA_50_ADDRESS

DA_51 = DA_50 + "d"
DA_51_ADDRESS = DA_50_ADDRESS
assert len(DA_51) == 51
assert DA_51_ADDRESS == DA_50_ADDRESS


def get_passphrase_choices(char: str) -> tuple[str, ...]:
    if char in " *#":
        return PASSPHRASE_LOWERCASE

    if char.islower():
        return PASSPHRASE_LOWERCASE
    elif char.isupper():
        return PASSPHRASE_UPPERCASE
    elif char.isdigit():
        return PASSPHRASE_DIGITS
    else:
        return PASSPHRASE_SPECIAL


def passphrase(char: str) -> Tuple[buttons.Coords, int]:
    choices = get_passphrase_choices(char)
    idx = next(i for i, letters in enumerate(choices) if char in letters)
    click_amount = choices[idx].index(char) + 1
    return buttons.pin_passphrase_index(idx), click_amount


@contextmanager
def prepare_passphrase_dialogue(
    device_handler: "BackgroundDeviceHandler", address: Optional[str] = None
) -> Generator["DebugLink", None, None]:
    debug = device_handler.debuglink()
    device_handler.run(get_test_address)  # type: ignore
    # TODO
    assert debug.read_layout().main_component() == "PassphraseKeyboard"

    # Resetting the category as it could have been changed by previous tests
    global KEYBOARD_CATEGORY
    KEYBOARD_CATEGORY = PassphraseCategory.LOWERCASE  # type: ignore

    yield debug

    result = device_handler.result()
    if address is not None:
        assert result == address


def go_to_category(debug: "DebugLink", category: PassphraseCategory) -> None:
    """Go to a specific category"""
    global KEYBOARD_CATEGORY
    global COORDS_PREV

    # Already there
    if KEYBOARD_CATEGORY == category:
        return

    current_index = KEYBOARD_CATEGORIES.index(KEYBOARD_CATEGORY)
    target_index = KEYBOARD_CATEGORIES.index(category)
    if target_index > current_index:
        for _ in range(target_index - current_index):
            debug.swipe_left()
    else:
        for _ in range(current_index - target_index):
            debug.swipe_right()
    KEYBOARD_CATEGORY = category  # type: ignore
    # Category changed, reset coordinates
    COORDS_PREV = (0, 0)  # type: ignore


def press_char(debug: "DebugLink", char: str) -> None:
    """Press a character"""
    global COORDS_PREV

    # Space and couple others are a special case
    if char in " *#":
        char_category = PassphraseCategory.LOWERCASE
    else:
        char_category = get_char_category(char)

    go_to_category(debug, char_category)

    coords, amount = passphrase(char)
    # If the button is the same as for the previous char,
    # waiting a second before pressing it again.
    if coords == COORDS_PREV:
        time.sleep(1.1)
    COORDS_PREV = coords  # type: ignore
    for _ in range(amount):
        debug.click(coords)


def input_passphrase(debug: "DebugLink", passphrase: str, check: bool = True) -> None:
    """Input a passphrase with validation it got added"""
    if check:
        before = debug.read_layout().passphrase()
    for char in passphrase:
        press_char(debug, char)
    if check:
        after = debug.read_layout().passphrase()
        assert after == before + passphrase


def enter_passphrase(debug: "DebugLink") -> None:
    """Enter a passphrase"""
    is_empty: bool = len(debug.read_layout().passphrase()) == 0
    coords = buttons.CORNER_BUTTON  # top-right corner
    debug.click(coords)
    if is_empty:
        debug.click(buttons.YES_UI_DELIZIA)


def delete_char(debug: "DebugLink") -> None:
    """Deletes the last char"""
    coords = buttons.pin_passphrase_grid(9)
    debug.click(coords)


VECTORS = (  # passphrase, address
    (CommonPass.SHORT, CommonPass.SHORT_ADDRESS),
    (CommonPass.WITH_SPACE, CommonPass.WITH_SPACE_ADDRESS),
    (CommonPass.RANDOM_25, CommonPass.RANDOM_25_ADDRESS),
    (DA_49, DA_49_ADDRESS),
    (DA_50, DA_50_ADDRESS),
)


@pytest.mark.parametrize("passphrase, address", VECTORS)
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_input(
    device_handler: "BackgroundDeviceHandler", passphrase: str, address: str
):
    with prepare_passphrase_dialogue(device_handler, address) as debug:
        input_passphrase(debug, passphrase)
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_input_over_50_chars(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, DA_51_ADDRESS) as debug:  # type: ignore
        input_passphrase(debug, DA_51, check=False)
        assert debug.read_layout().passphrase() == DA_50
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_delete(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, CommonPass.SHORT_ADDRESS) as debug:
        input_passphrase(debug, CommonPass.SHORT[:8])

        for _ in range(4):
            delete_char(debug)
        debug.read_layout()

        input_passphrase(debug, CommonPass.SHORT[8 - 4 :])
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_delete_all(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        passphrase = "trezor"
        input_passphrase(debug, passphrase)

        for _ in range(len(passphrase)):
            delete_char(debug)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_loop_all_characters(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        for category in (
            PassphraseCategory.DIGITS,
            PassphraseCategory.LOWERCASE,
            PassphraseCategory.UPPERCASE,
            PassphraseCategory.SPECIAL,
        ):
            go_to_category(debug, category)
        debug.read_layout()

        enter_passphrase(debug)
        coords = buttons.pin_passphrase_grid(11)
        debug.click(coords)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_click_same_button_many_times(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler) as debug:
        a_coords, _ = buttons.passphrase("a")
        for _ in range(10):
            debug.click(a_coords)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_prompt_disappears(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler) as debug:
        input_passphrase(debug, "a")

        # Wait a second for the prompt to disappear
        time.sleep(1.1)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_long_spaces_deletion(
    device_handler: "BackgroundDeviceHandler",
):
    with prepare_passphrase_dialogue(device_handler) as debug:
        input_passphrase(
            debug,
            "a"
            + " " * 7
            + "b"
            + " " * 7
            + "c"
            + " " * 7
            + "d"
            + " " * 7
            + "e"
            + " " * 7
            + "f",
        )
        for _ in range(12):
            delete_char(debug)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_dollar_sign_deletion(
    device_handler: "BackgroundDeviceHandler",
):
    # Checks that dollar signs will not leave one pixel on the top after deleting
    # (was a bug previously on model T)
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        passphrase = "$$ I want $$"
        input_passphrase(debug, passphrase)

        for _ in range(len(passphrase)):
            delete_char(debug)

        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_cycle_through_last_character(
    device_handler: "BackgroundDeviceHandler",
):
    # Checks that we can cycle through the last (50th) passphrase character
    # (was a bug previously)
    with prepare_passphrase_dialogue(device_handler) as debug:
        passphrase = DA_49 + "i"  # for i we need to cycle through "ghi" three times
        input_passphrase(debug, passphrase)
        enter_passphrase(debug)
