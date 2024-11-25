from __future__ import annotations

import typing as t
from enum import Enum

from trezorlib.debuglink import LayoutType

from .. import buttons
from .. import translations as TR

if t.TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent

    AllActionsType = t.List[t.Union[str, t.Tuple[str, ...]]]


# Passphrases and addresses for both models
class CommonPass:
    RANDOM_25 = "Y@14lw%p)JN@f54MYvys@zj'g"
    RANDOM_25_ADDRESS = "mnkoxeaMzLgfCxUdDSZWrGactyJJerQVW6"

    SHORT = "abc123ABC_<>"
    SHORT_ADDRESS = "mtHHfh6uHtJiACwp7kzJZ97yueT6sEdQiG"

    WITH_SPACE = "abc 123"
    WITH_SPACE_ADDRESS = "mvqzZUb9NaUc62Buk9WCP4L7hunsXFyamT"

    EMPTY_ADDRESS = "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"


class PassphraseCategory(Enum):
    MENU = "MENU"
    DIGITS = "123"
    LOWERCASE = "abc"
    UPPERCASE = "ABC"
    SPECIAL = "#$!"


def get_char_category(char: str) -> PassphraseCategory:
    """What is the category of a character"""
    if char.isdigit():
        return PassphraseCategory.DIGITS
    if char.islower():
        return PassphraseCategory.LOWERCASE
    if char.isupper():
        return PassphraseCategory.UPPERCASE
    return PassphraseCategory.SPECIAL


def go_next(debug: "DebugLink") -> LayoutContent:
    if debug.layout_type is LayoutType.TT:
        return debug.click(buttons.OK)
    elif debug.layout_type is LayoutType.TR:
        return debug.press_right()
    elif debug.layout_type is LayoutType.Mercury:
        return debug.swipe_up()
    else:
        raise RuntimeError("Unknown model")


def tap_to_confirm(debug: "DebugLink") -> LayoutContent:
    if debug.layout_type is LayoutType.TT:
        return debug.read_layout()
    elif debug.layout_type is LayoutType.TR:
        return debug.read_layout()
    elif debug.layout_type is LayoutType.Mercury:
        return debug.click(buttons.TAP_TO_CONFIRM)
    else:
        raise RuntimeError("Unknown model")


def go_back(debug: "DebugLink", r_middle: bool = False) -> LayoutContent:
    if debug.layout_type in (LayoutType.TT, LayoutType.Mercury):
        return debug.click(buttons.CANCEL)
    elif debug.layout_type is LayoutType.TR:
        if r_middle:
            return debug.press_middle()
        else:
            return debug.press_left()
    else:
        raise RuntimeError("Unknown model")


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
            layout = debug.press_left()
    else:
        for _ in range(steps):
            layout = debug.press_right()

    # Press or hold
    debug.press_middle(hold_ms=hold_ms)


def _carousel_steps(current_index: int, wanted_index: int, length: int) -> int:
    steps_forward = (wanted_index - current_index) % length
    steps_backward = (current_index - wanted_index) % length
    return steps_forward if steps_forward <= steps_backward else -steps_backward


def unlock_gesture(debug: "DebugLink") -> LayoutContent:
    if debug.layout_type is LayoutType.TT:
        return debug.click(buttons.OK)
    elif debug.layout_type is LayoutType.TR:
        return debug.press_right()
    elif debug.layout_type is LayoutType.Mercury:
        return debug.click(buttons.TAP_TO_CONFIRM)
    else:
        raise RuntimeError("Unknown model")


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
