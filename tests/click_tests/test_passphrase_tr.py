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

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator, Optional

import pytest

from trezorlib import exceptions

from .. import translations as TR
from ..common import get_test_address
from .common import (
    CommonPass,
    PassphraseCategory,
    get_char_category,
    navigate_to_action_and_press,
)

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ..device_handler import BackgroundDeviceHandler


pytestmark = [pytest.mark.skip_t1, pytest.mark.skip_t2]

# Testing the maximum length is really 50
# TODO: show some UI message when length reaches 50?

AAA_50 = 50 * "a"
AAA_50_ADDRESS = "miPeCUxf1Ufh5DtV3AuBopNM8YEDvnQZMh"
assert len(AAA_50) == 50

AAA_49 = AAA_50[:-1]
AAA_49_ADDRESS = "n2MPUjAB86MuVmyYe8HCgdznJS1FXk3qvg"
assert len(AAA_49) == 49
assert AAA_49_ADDRESS != AAA_50_ADDRESS

AAA_51 = AAA_50 + "a"
AAA_51_ADDRESS = "miPeCUxf1Ufh5DtV3AuBopNM8YEDvnQZMh"
assert len(AAA_51) == 51
assert AAA_51_ADDRESS == AAA_50_ADDRESS


def _get_possible_btns(path: str) -> str:
    return "|".join(TR.translate(path))


def _get_cancel_or_delete() -> str:
    paths = ["inputs__cancel", "inputs__delete"]
    return "|".join(_get_possible_btns(path) for path in paths)


BACK = _get_possible_btns("inputs__back")
SHOW = _get_possible_btns("inputs__show")
ENTER = _get_possible_btns("inputs__enter")
SPACE = _get_possible_btns("inputs__space")
CANCEL_OR_DELETE = _get_cancel_or_delete()
# fmt: off
MENU_ACTIONS = [SHOW, CANCEL_OR_DELETE, ENTER, "abc", "ABC", "123", "#$!", SPACE]
DIGITS_ACTIONS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", BACK]
LOWERCASE_ACTIONS = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s",
    "t", "u", "v", "w", "x", "y", "z", BACK
]
UPPERCASE_ACTIONS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
    "T", "U", "V", "W", "X", "Y", "Z", BACK
]
SPECIAL_ACTIONS = [
    "_", "<", ">", ".", ":", "@", "/", "|", "\\", "!", "(", ")", "+", "%", "&", "-", "[", "]", "?",
    "{", "}", ",", "'", "`", ";", "\"", "~", "$", "^", "=", "*", "#", BACK
]
# fmt: on

CATEGORY_ACTIONS = {
    PassphraseCategory.MENU: MENU_ACTIONS,
    PassphraseCategory.DIGITS: DIGITS_ACTIONS,
    PassphraseCategory.LOWERCASE: LOWERCASE_ACTIONS,
    PassphraseCategory.UPPERCASE: UPPERCASE_ACTIONS,
    PassphraseCategory.SPECIAL: SPECIAL_ACTIONS,
}


@contextmanager
def prepare_passphrase_dialogue(
    device_handler: "BackgroundDeviceHandler", address: Optional[str] = None
) -> Generator["DebugLink", None, None]:
    debug = device_handler.debuglink()
    device_handler.run(get_test_address)  # type: ignore
    layout = debug.wait_layout()
    assert "PassphraseKeyboard" in layout.all_components()
    assert layout.passphrase() == ""
    assert _current_category(debug) == PassphraseCategory.MENU

    yield debug

    result = device_handler.result()
    if address is not None:
        assert result == address


def _current_category(debug: "DebugLink") -> PassphraseCategory:
    """What is the current category we are in"""
    layout = debug.read_layout()
    category = layout.find_unique_value_by_key("current_category", "")
    return PassphraseCategory(category)


def _current_actions(debug: "DebugLink") -> list[str]:
    """What are the actions in the current category"""
    current = _current_category(debug)
    return CATEGORY_ACTIONS[current]


def go_to_category(
    debug: "DebugLink", category: PassphraseCategory, use_carousel: bool = True
) -> None:
    """Go to a specific category"""
    # Already there
    if _current_category(debug) == category:
        return

    # Need to be in MENU anytime to change category
    if _current_category(debug) != PassphraseCategory.MENU:
        navigate_to_action_and_press(
            debug, BACK, _current_actions(debug), is_carousel=use_carousel
        )

    assert _current_category(debug) == PassphraseCategory.MENU

    # Go to the right one, unless we want MENU
    if category != PassphraseCategory.MENU:
        navigate_to_action_and_press(
            debug, category.value, _current_actions(debug), is_carousel=use_carousel
        )

    assert _current_category(debug) == category


def press_char(debug: "DebugLink", char: str) -> None:
    """Press a character"""
    # Space is a special case
    if char == " ":
        go_to_category(debug, PassphraseCategory.MENU)
        navigate_to_action_and_press(debug, SPACE, _current_actions(debug))
    else:
        char_category = get_char_category(char)
        go_to_category(debug, char_category)
        navigate_to_action_and_press(debug, char, _current_actions(debug))


def input_passphrase(debug: "DebugLink", passphrase: str) -> None:
    """Input a passphrase with validation it got added"""
    before = debug.read_layout().passphrase()
    for char in passphrase:
        press_char(debug, char)
    after = debug.read_layout().passphrase()
    assert after == before + passphrase


def show_passphrase(debug: "DebugLink") -> None:
    """Show a passphrase"""
    go_to_category(debug, PassphraseCategory.MENU)
    navigate_to_action_and_press(debug, SHOW, _current_actions(debug))


def enter_passphrase(debug: "DebugLink") -> None:
    """Enter a passphrase"""
    go_to_category(debug, PassphraseCategory.MENU)
    navigate_to_action_and_press(debug, ENTER, _current_actions(debug))


def delete_char(debug: "DebugLink") -> None:
    """Deletes the last char"""
    go_to_category(debug, PassphraseCategory.MENU)
    navigate_to_action_and_press(debug, CANCEL_OR_DELETE, _current_actions(debug))


def cancel(debug: "DebugLink") -> None:
    """Cancels the whole dialogue - clicking the same button as in DELETE"""
    delete_char(debug)


VECTORS = (  # passphrase, address
    (CommonPass.SHORT, CommonPass.SHORT_ADDRESS),
    (CommonPass.WITH_SPACE, CommonPass.WITH_SPACE_ADDRESS),
    (CommonPass.RANDOM_25, CommonPass.RANDOM_25_ADDRESS),
    (AAA_49, AAA_49_ADDRESS),
    (AAA_50, AAA_50_ADDRESS),
)


@pytest.mark.parametrize("passphrase, address", VECTORS)
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_input(
    device_handler: "BackgroundDeviceHandler", passphrase: str, address: str
):
    with prepare_passphrase_dialogue(device_handler, address) as debug:
        input_passphrase(debug, passphrase)
        show_passphrase(debug)
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_input_over_50_chars(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, AAA_51_ADDRESS) as debug:  # type: ignore
        # First 50 chars
        input_passphrase(debug, AAA_51[:-1])
        layout = debug.read_layout()
        assert AAA_51[:-1] in layout.passphrase()

        show_passphrase(debug)

        # Over-limit character
        press_char(debug, AAA_51[-1])

        # No change
        layout = debug.read_layout()
        assert AAA_51[:-1] in layout.passphrase()
        assert AAA_51 not in layout.passphrase()

        show_passphrase(debug)
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_delete(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, CommonPass.SHORT_ADDRESS) as debug:
        input_passphrase(debug, CommonPass.SHORT[:8])
        show_passphrase(debug)

        for _ in range(4):
            delete_char(debug)
        show_passphrase(debug)

        input_passphrase(debug, CommonPass.SHORT[8 - 4 :])
        show_passphrase(debug)
        enter_passphrase(debug)


@pytest.mark.setup_client(passphrase=True)
def test_cancel(device_handler: "BackgroundDeviceHandler"):
    with pytest.raises(exceptions.Cancelled):
        with prepare_passphrase_dialogue(device_handler) as debug:
            input_passphrase(debug, "abc")
            show_passphrase(debug)
            for _ in range(3):
                delete_char(debug)
            show_passphrase(debug)
            cancel(debug)


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_loop_all_characters(device_handler: "BackgroundDeviceHandler"):
    with prepare_passphrase_dialogue(device_handler, CommonPass.EMPTY_ADDRESS) as debug:
        for category in PassphraseCategory:
            go_to_category(debug, category)
            # use_carousel=False because we want to reach BACK at the end of the list
            go_to_category(debug, PassphraseCategory.MENU, use_carousel=False)

        enter_passphrase(debug)
