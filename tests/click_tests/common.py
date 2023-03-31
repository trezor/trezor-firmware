from enum import Enum
from typing import TYPE_CHECKING

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


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


def go_next(debug: "DebugLink", wait: bool = False) -> None:
    if debug.model == "T":
        debug.click(buttons.OK, wait=wait)  # type: ignore
    elif debug.model == "R":
        debug.press_right(wait=wait)  # type: ignore


def go_back(debug: "DebugLink", wait: bool = False) -> None:
    if debug.model == "T":
        debug.click(buttons.CANCEL, wait=wait)  # type: ignore
    elif debug.model == "R":
        debug.press_left(wait=wait)  # type: ignore


def navigate_to_action_and_press(
    debug: "DebugLink",
    wanted_action: str,
    all_actions: list[str],
    is_carousel: bool = True,
) -> None:
    """Navigate to the button with certain action and press it"""
    # Orient
    if wanted_action not in all_actions:
        raise ValueError(f"Action {wanted_action} is not supported in {all_actions}")

    def current_action() -> str:
        return layout.buttons.get_middle_select()

    # Navigate
    layout = debug.read_layout()
    while current_action() != wanted_action:
        layout = _move_one_closer(
            debug=debug,
            wanted_action=wanted_action,
            current_action=current_action(),
            all_actions=all_actions,
            is_carousel=is_carousel,
        )

    # Press
    debug.press_middle(wait=True)


def _move_one_closer(
    debug: "DebugLink",
    wanted_action: str,
    current_action: str,
    all_actions: list[str],
    is_carousel: bool,
) -> "LayoutContent":
    """Pressing either left or right regarding to the current situation"""
    index_diff = all_actions.index(wanted_action) - all_actions.index(current_action)
    if not is_carousel:
        # Simply move according to the index in a closed list
        if index_diff > 0:
            return debug.press_right(wait=True)
        else:
            return debug.press_left(wait=True)
    else:
        # Carousel can move in a circle - over the edges
        # Always move the shortest way
        action_half = len(all_actions) // 2
        if index_diff > action_half or -action_half < index_diff < 0:
            return debug.press_left(wait=True)
        else:
            return debug.press_right(wait=True)
