from __future__ import annotations

import time
import typing as t
from enum import Enum

from trezorlib.debuglink import LayoutType

from .. import translations as TR

if t.TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent

    AllActionsType = list[str | tuple[str, ...]]


# Passphrases and addresses for both models
class CommonPass:
    RANDOM_25 = "Y@14lw%p)JN@f54MYvys@zj'g"
    RANDOM_25_ADDRESS = "mnkoxeaMzLgfCxUdDSZWrGactyJJerQVW6"

    SHORT = "abc123ABC_<>"
    SHORT_ADDRESS = "mtHHfh6uHtJiACwp7kzJZ97yueT6sEdQiG"

    WITH_SPACE = "abc 123"
    WITH_SPACE_ADDRESS = "mvqzZUb9NaUc62Buk9WCP4L7hunsXFyamT"

    EMPTY_ADDRESS = "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"


# Passphrase/Label keyboard layouts
class KeyboardCategory(Enum):
    Menu = "MENU"
    Numeric = "123"
    LettersLower = "abc"
    LettersUpper = "ABC"
    Special = "#$!"


KEYBOARD_CATEGORIES_BOLT = [
    KeyboardCategory.Numeric,
    KeyboardCategory.LettersLower,
    KeyboardCategory.LettersUpper,
    KeyboardCategory.Special,
]

# Common for Delizia and Eckhart
KEYBOARD_CATEGORIES_DE = [
    KeyboardCategory.LettersLower,
    KeyboardCategory.LettersUpper,
    KeyboardCategory.Numeric,
    KeyboardCategory.Special,
]

COORDS_PREV: tuple[int, int] = (0, 0)


def get_char_category(char: str) -> KeyboardCategory:
    """What is the category of a character"""
    if char.isdigit():
        return KeyboardCategory.Numeric
    if char.islower():
        return KeyboardCategory.LettersLower
    if char.isupper():
        return KeyboardCategory.LettersUpper
    return KeyboardCategory.Special


def go_next(debug: "DebugLink") -> LayoutContent:
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.ok())
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
    else:
        raise RuntimeError("Unknown model")
    return debug.read_layout()


def go_back(debug: "DebugLink", r_middle: bool = False) -> LayoutContent:
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.cancel())
    elif debug.layout_type is LayoutType.Caesar:
        if r_middle:
            debug.press_middle()
        else:
            debug.press_left()
    else:
        raise RuntimeError("Unknown model")
    return debug.read_layout()


def navigate_to_action_and_press(
    debug: "DebugLink",
    wanted_action: str,
    all_actions: AllActionsType,
    is_carousel: bool = True,
    hold_ms: int = 0,
) -> None:
    """Navigate to the button with certain action and press it"""
    # Orient
    try:
        _get_action_index(wanted_action, all_actions)
    except ValueError:
        raise ValueError(f"Action {wanted_action} is not supported in {all_actions}")

    # Navigate
    layout = debug.read_layout()
    current_action = layout.get_middle_choice()
    current_index = _get_action_index(current_action, all_actions)
    wanted_index = _get_action_index(wanted_action, all_actions)

    if not is_carousel:
        steps = wanted_index - current_index
    else:
        steps = _carousel_steps(current_index, wanted_index, len(all_actions))

    if steps < 0:
        for _ in range(-steps):
            debug.press_left()
    else:
        for _ in range(steps):
            debug.press_right()

    # Press or hold
    debug.press_middle(hold_ms=hold_ms)


def _carousel_steps(current_index: int, wanted_index: int, length: int) -> int:
    steps_forward = (wanted_index - current_index) % length
    steps_backward = (current_index - wanted_index) % length
    return steps_forward if steps_forward <= steps_backward else -steps_backward


def unlock_gesture(debug: "DebugLink") -> LayoutContent:
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
        debug.click(debug.screen_buttons.ok())
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
    elif debug.layout_type is LayoutType.Delizia:
        debug.click(debug.screen_buttons.tap_to_confirm())
    else:
        raise RuntimeError("Unknown model")
    return debug.read_layout()


def _get_action_index(wanted_action: str, all_actions: AllActionsType) -> int:
    """Get index of the action in the list of all actions"""
    if wanted_action in all_actions:
        return all_actions.index(wanted_action)
    for index, action in enumerate(all_actions):
        if not isinstance(action, tuple):
            action = (action,)
        for subaction in action:
            try:
                tr = TR.translate(subaction)
            except KeyError:
                continue
            if tr == wanted_action:
                return index

    raise ValueError(f"Action {wanted_action} is not supported in {all_actions}")


def keyboard_categories(layout_type: LayoutType) -> list[KeyboardCategory]:
    if layout_type is LayoutType.Bolt:
        return KEYBOARD_CATEGORIES_BOLT
    elif layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
        return KEYBOARD_CATEGORIES_DE
    else:
        raise ValueError("Wrong layout type")


def get_category(debug: "DebugLink") -> KeyboardCategory:
    category = debug.read_layout().find_unique_value_by_key(
        "active_layout", default="", only_type=str
    )
    assert (
        category in KeyboardCategory.__members__
    ), f"Unknown layout name from debug: {category}"
    return KeyboardCategory[category]


def go_to_category(
    debug: "DebugLink", category: KeyboardCategory, verify_layout: bool = False
) -> None:
    """
    Go to a specific category on the passphrase/label keyboard.

    Navigates through the on-screen categories by swiping left or right
    until the desired category is reached. If `verify_layout` is set to True,
    the function will assert that the category change has been correctly applied
    by reading and validating the current layout from the debug interface.
    """
    global COORDS_PREV

    keyboard_category = get_category(debug)

    # Already there
    if keyboard_category == category:
        return

    current_index = keyboard_categories(debug.layout_type).index(keyboard_category)
    target_index = keyboard_categories(debug.layout_type).index(category)
    if target_index > current_index:
        for _ in range(target_index - current_index):
            debug.swipe_left()
    else:
        for _ in range(current_index - target_index):
            debug.swipe_right()
    if verify_layout:
        layout = get_category(debug)
        assert layout == category, f"Layout mismatch: expected {category}, got {layout}"

    # Category changed, reset coordinates
    COORDS_PREV = (0, 0)  # type: ignore


def press_char(debug: "DebugLink", char: str) -> None:
    """Press a character on the passphrase/label keyboard."""
    global COORDS_PREV

    # Space and couple others are a special case
    if char in " *#":
        char_category = KeyboardCategory.LettersLower
    else:
        char_category = get_char_category(char)

    go_to_category(debug, char_category)

    coords, amount = debug.button_actions.passphrase(char)
    # If the button is the same as for the previous char,
    # waiting a second before pressing it again.
    # (not for a space in Bolt layout)
    is_bolt_space = debug.layout_type is LayoutType.Bolt and char == " "
    if coords == COORDS_PREV and not is_bolt_space:
        time.sleep(1.1)
    COORDS_PREV = coords  # type: ignore
    for _ in range(amount):
        debug.click(coords)


def delete_char(debug: "DebugLink") -> None:
    """Deletes the last char"""
    debug.click(debug.screen_buttons.pin_passphrase_erase())
