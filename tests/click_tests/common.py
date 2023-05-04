from __future__ import annotations

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


def go_next(debug: "DebugLink", wait: bool = False) -> "LayoutContent" | None:
    return debug.click(buttons.OK, wait=wait)  # type: ignore


def go_back(debug: "DebugLink", wait: bool = False) -> "LayoutContent" | None:
    return debug.click(buttons.CANCEL, wait=wait)  # type: ignore
