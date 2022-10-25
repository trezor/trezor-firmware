import time
from typing import Iterator, Tuple

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

CONFIRM_WORD = (MID, TOP)

RESET_MINUS = (LEFT, grid(DISPLAY_HEIGHT, 5, 1))
RESET_PLUS = (RIGHT, grid(DISPLAY_HEIGHT, 5, 1))

RESET_WORD_CHECK = [
    (MID, grid(DISPLAY_HEIGHT, 5, 2)),
    (MID, grid(DISPLAY_HEIGHT, 5, 3)),
    (MID, grid(DISPLAY_HEIGHT, 5, 4)),
]


BUTTON_LETTERS_BIP39 = ("abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz")
BUTTON_LETTERS_SLIP39 = ("ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz")


def grid35(x: int, y: int) -> Tuple[int, int]:
    return grid(DISPLAY_WIDTH, 3, x), grid(DISPLAY_HEIGHT, 5, y)


def grid34(x: int, y: int) -> Tuple[int, int]:
    return grid(DISPLAY_WIDTH, 3, x), grid(DISPLAY_HEIGHT, 4, y)


def _grid34_from_index(idx: int) -> Tuple[int, int]:
    grid_x = idx % 3
    grid_y = idx // 3 + 1  # first line is empty
    return grid34(grid_x, grid_y)


def type_word(word: str, is_slip39: bool = False) -> Iterator[Tuple[int, int]]:
    if is_slip39:
        yield from type_word_slip39(word)
    else:
        yield from type_word_bip39(word)


def type_word_slip39(word: str) -> Iterator[Tuple[int, int]]:
    for l in word:
        idx = next(i for i, letters in enumerate(BUTTON_LETTERS_SLIP39) if l in letters)
        yield _grid34_from_index(idx)


def type_word_bip39(word: str) -> Iterator[Tuple[int, int]]:
    coords_prev: Tuple[int, int] | None = None
    for letter in word:
        coords, amount = letter_coords_and_amount(letter)
        # If the button is the same as for the previous letter,
        # waiting a second before pressing it again.
        if coords == coords_prev:
            time.sleep(1)
        coords_prev = coords
        for _ in range(amount):
            yield coords


def letter_coords_and_amount(letter: str) -> Tuple[Tuple[int, int], int]:
    idx = next(i for i, letters in enumerate(BUTTON_LETTERS_BIP39) if letter in letters)
    click_amount = BUTTON_LETTERS_BIP39[idx].index(letter) + 1
    return _grid34_from_index(idx), click_amount
