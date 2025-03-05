import time
from typing import Iterator, Tuple

from trezorlib.debuglink import LayoutType

Coords = Tuple[int, int]


# display dimensions
def display_height(layout_type):
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return 240
    else:
        raise ValueError("Wrong layout type")


def display_width(layout_type):
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return 240
    else:
        raise ValueError("Wrong layout type")


# grid coordinates
def grid(dim: int, grid_cells: int, cell: int) -> int:
    step = dim // grid_cells
    ofs = step // 2
    return cell * step + ofs


def grid35(x: int, y: int, layout_type: LayoutType) -> Coords:
    return grid(display_width(layout_type), 3, x), grid(
        display_height(layout_type), 5, y
    )


def grid34(x: int, y: int, layout_type: LayoutType) -> Coords:
    assert layout_type in (LayoutType.Bolt, LayoutType.Delizia)
    return grid(display_width(layout_type), 3, x), grid(
        display_height(layout_type), 4, y
    )


def _grid34_from_index(idx: int, layout_type: LayoutType) -> Coords:
    assert layout_type in (LayoutType.Bolt, LayoutType.Delizia)
    grid_x = idx % 3
    grid_y = idx // 3 + 1  # first line is empty
    return grid34(grid_x, grid_y, layout_type)


# Horizontal coordinates
def left(layout_type: LayoutType):
    return grid(display_width(layout_type), 3, 0)


def mid(layout_type: LayoutType):
    return grid(display_width(layout_type), 3, 1)


def right(layout_type: LayoutType):
    return grid(display_width(layout_type), 3, 2)


# Vertical coordinates
def top(layout_type: LayoutType):
    return grid(display_height(layout_type), 6, 0)


def bottom(layout_type: LayoutType):
    return grid(display_height(layout_type), 6, 5)


# Buttons


def ok(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return (right(layout_type), bottom(layout_type))
    else:
        raise ValueError("Wrong layout type")


def cancel(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return (left(layout_type), bottom(layout_type))
    else:
        raise ValueError("Wrong layout type")


def info(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return (mid(layout_type), bottom(layout_type))
    else:
        raise ValueError("Wrong layout type")


def recovery_delete(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return (left(layout_type), top(layout_type))
    else:
        raise ValueError("Wrong layout type")


def corner_button(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return (215, 25)
    else:
        raise ValueError("Wrong layout type")


def confirm_word(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return (mid(layout_type), top(layout_type))
    else:
        raise ValueError("Wrong layout type")


# PIN/passphrase input
def input(layout_type: LayoutType) -> Coords:
    return (mid(layout_type), top(layout_type))


# Yes/No decision component
def ui_yes(layout_type: LayoutType) -> Coords:
    assert layout_type is LayoutType.Delizia
    return grid34(2, 2, layout_type)


def ui_no(layout_type: LayoutType) -> Coords:
    assert layout_type is LayoutType.Delizia
    return grid34(0, 2, layout_type)


# +/- buttons in number input component
def reset_minus(layout_type: LayoutType) -> Coords:
    if layout_type is LayoutType.Bolt:
        return (left(layout_type), grid(display_height(layout_type), 5, 1))
    elif layout_type is LayoutType.Delizia:
        return (left(layout_type), grid(display_height(layout_type), 5, 3))
    else:
        raise ValueError("Wrong layout type")


def reset_plus(layout_type: LayoutType) -> Coords:
    if layout_type is LayoutType.Bolt:
        return (right(layout_type), grid(display_height(layout_type), 5, 1))
    elif layout_type is LayoutType.Delizia:
        return (right(layout_type), grid(display_height(layout_type), 5, 3))
    else:
        raise ValueError("Wrong layout type")


# select word component buttons
def reset_word_check(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return [
            (mid(layout_type), grid(display_height(layout_type), 5, 2)),
            (mid(layout_type), grid(display_height(layout_type), 5, 3)),
            (mid(layout_type), grid(display_height(layout_type), 5, 4)),
        ]
    else:
        raise ValueError("Wrong layout type")


# vertical menu buttons
def vertical_menu(layout_type: LayoutType) -> Coords:
    if layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        return [
            (mid(layout_type), grid(display_height(layout_type), 4, 1)),
            (mid(layout_type), grid(display_height(layout_type), 4, 2)),
            (mid(layout_type), grid(display_height(layout_type), 4, 3)),
        ]
    else:
        raise ValueError("Wrong layout type")


def tap_to_confirm(layout_type: LayoutType) -> Coords:
    assert layout_type is LayoutType.Delizia
    return vertical_menu(layout_type)[1]


BUTTON_LETTERS_BIP39 = ("abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz")
BUTTON_LETTERS_SLIP39 = ("ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz")

# fmt: off
PASSPHRASE_LOWERCASE = (" ", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#")
PASSPHRASE_UPPERCASE = (" ", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#")
PASSPHRASE_DIGITS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
PASSPHRASE_SPECIAL = ("_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^=")
# fmt: on


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


def passphrase(char: str, layout_type: LayoutType) -> Tuple[Coords, int]:
    choices = get_passphrase_choices(char)
    idx = next(i for i, letters in enumerate(choices) if char in letters)
    click_amount = choices[idx].index(char) + 1
    return pin_passphrase_index(idx, layout_type), click_amount


def pin_passphrase_index(idx: int, layout_type: LayoutType) -> Coords:
    if idx == 9:
        idx = 10  # last digit is in the middle
    return pin_passphrase_grid(idx, layout_type)


def pin_passphrase_grid(idx: int, layout_type: LayoutType) -> Coords:
    grid_x = idx % 3
    grid_y = idx // 3 + 1  # first line is empty
    return grid35(grid_x, grid_y, layout_type)


def type_word(layout_type: LayoutType, word: str, is_slip39: bool = False) -> Iterator[Coords]:
    if is_slip39:
        yield from _type_word_slip39(word, layout_type)
    else:
        yield from _type_word_bip39(word, layout_type)


def _type_word_slip39(word: str, layout_type: LayoutType) -> Iterator[Coords]:
    for l in word:
        idx = next(i for i, letters in enumerate(BUTTON_LETTERS_SLIP39) if l in letters)
        yield _grid34_from_index(idx, layout_type)


def _type_word_bip39(word: str, layout_type: LayoutType) -> Iterator[Coords]:
    coords_prev: Coords | None = None
    for letter in word:
        time.sleep(0.1)  # not being so quick to miss something
        coords, amount = _letter_coords_and_amount(letter, layout_type)
        # If the button is the same as for the previous letter,
        # waiting a second before pressing it again.
        if coords == coords_prev:
            time.sleep(1.1)
        coords_prev = coords
        for _ in range(amount):
            yield coords


def _letter_coords_and_amount(letter: str, layout_type: LayoutType) -> Tuple[Coords, int]:
    idx = next(i for i, letters in enumerate(BUTTON_LETTERS_BIP39) if letter in letters)
    click_amount = BUTTON_LETTERS_BIP39[idx].index(letter) + 1
    return _grid34_from_index(idx, layout_type), click_amount
