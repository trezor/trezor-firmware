import time
from typing import Iterator, Tuple

Coords = Tuple[int, int]

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240


def grid(dim: int, grid_cells: int, cell: int) -> int:
    step = dim // grid_cells
    ofs = step // 2
    return cell * step + ofs


LEFT = grid(DISPLAY_WIDTH, 3, 0)
MID = grid(DISPLAY_WIDTH, 3, 1)
RIGHT = grid(DISPLAY_WIDTH, 3, 2)

TOP = grid(DISPLAY_HEIGHT, 4, 0)
BOTTOM = grid(DISPLAY_HEIGHT, 4, 3)

OK = (RIGHT, BOTTOM)
CANCEL = (LEFT, BOTTOM)
INFO = (MID, BOTTOM)

RECOVERY_DELETE = (LEFT, TOP)

CORNER_BUTTON = (215, 25)

CONFIRM_WORD = (MID, TOP)
TOP_ROW = (MID, TOP)

RESET_MINUS = (LEFT, grid(DISPLAY_HEIGHT, 5, 1))
RESET_PLUS = (RIGHT, grid(DISPLAY_HEIGHT, 5, 1))

RESET_WORD_CHECK = [
    (MID, grid(DISPLAY_HEIGHT, 5, 2)),
    (MID, grid(DISPLAY_HEIGHT, 5, 3)),
    (MID, grid(DISPLAY_HEIGHT, 5, 4)),
]


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


def passphrase(char: str) -> Tuple[Coords, int]:
    choices = get_passphrase_choices(char)
    idx = next(i for i, letters in enumerate(choices) if char in letters)
    click_amount = choices[idx].index(char) + 1
    return pin_passphrase_index(idx), click_amount


def pin_passphrase_index(idx: int) -> Coords:
    if idx == 9:
        idx = 10  # last digit is in the middle
    return pin_passphrase_grid(idx)


def pin_passphrase_grid(idx: int) -> Coords:
    grid_x = idx % 3
    grid_y = idx // 3 + 1  # first line is empty
    return grid35(grid_x, grid_y)


def grid35(x: int, y: int) -> Coords:
    return grid(DISPLAY_WIDTH, 3, x), grid(DISPLAY_HEIGHT, 5, y)


def grid34(x: int, y: int) -> Coords:
    return grid(DISPLAY_WIDTH, 3, x), grid(DISPLAY_HEIGHT, 4, y)


def _grid34_from_index(idx: int) -> Coords:
    grid_x = idx % 3
    grid_y = idx // 3 + 1  # first line is empty
    return grid34(grid_x, grid_y)


def type_word(word: str, is_slip39: bool = False) -> Iterator[Coords]:
    if is_slip39:
        yield from _type_word_slip39(word)
    else:
        yield from _type_word_bip39(word)


def _type_word_slip39(word: str) -> Iterator[Coords]:
    for l in word:
        idx = next(i for i, letters in enumerate(BUTTON_LETTERS_SLIP39) if l in letters)
        yield _grid34_from_index(idx)


def _type_word_bip39(word: str) -> Iterator[Coords]:
    coords_prev: Coords | None = None
    for letter in word:
        time.sleep(0.1)  # not being so quick to miss something
        coords, amount = _letter_coords_and_amount(letter)
        # If the button is the same as for the previous letter,
        # waiting a second before pressing it again.
        if coords == coords_prev:
            time.sleep(1.1)
        coords_prev = coords
        for _ in range(amount):
            yield coords


def _letter_coords_and_amount(letter: str) -> Tuple[Coords, int]:
    idx = next(i for i, letters in enumerate(BUTTON_LETTERS_BIP39) if letter in letters)
    click_amount = BUTTON_LETTERS_BIP39[idx].index(letter) + 1
    return _grid34_from_index(idx), click_amount
