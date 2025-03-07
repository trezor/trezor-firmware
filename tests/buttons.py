import time
from typing import Iterator, Tuple

from trezorlib.debuglink import LayoutType

Coords = Tuple[int, int]


class ScreenButtons:
    def __init__(self, layout_type: LayoutType):
        assert layout_type in (LayoutType.Bolt, LayoutType.Delizia)
        self.layout_type = layout_type

    def _width(self) -> int:
        return 240

    def _height(self) -> int:
        return 240

    def _grid(self, dim: int, grid_cells: int, cell: int) -> int:
        assert cell < grid_cells
        step = dim // grid_cells
        ofs = step // 2
        return cell * step + ofs

    # 3 columns, 4 rows, 1st row is input area
    def _grid35(self, x: int, y: int) -> Coords:
        return self._grid(self._width(), 3, x), self._grid(self._height(), 5, y)

    # TODO: do not expose this
    # 3 columns, 3 rows, 1st row is input area
    def grid34(self, x: int, y: int) -> Coords:
        return self._grid(self._width(), 3, x), self._grid(self._height(), 4, y)

    # Horizontal coordinates
    def _left(self) -> int:
        return self._grid(self._width(), 3, 0)

    def _mid(self) -> int:
        return self._grid(self._width(), 3, 1)

    def _right(self) -> int:
        return self._grid(self._width(), 3, 2)

    # Vertical coordinates
    def _top(self) -> int:
        return self._grid(self._height(), 6, 0)

    def _bottom(self) -> int:
        return self._grid(self._height(), 6, 5)

    # Buttons

    # Right bottom
    def ok(self) -> Coords:
        return (self._right(), self._bottom())

    # Left bottom
    def cancel(self) -> Coords:
        return (self._left(), self._bottom())

    # Mid bottom
    def info(self) -> Coords:
        return (self._mid(), self._bottom())

    # Menu/close menu button
    def menu(self) -> Coords:
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return (215, 25)
        else:
            raise ValueError("Wrong layout type")

    # Center of the screen
    def tap_to_confirm(self) -> Coords:
        assert self.layout_type is LayoutType.Delizia
        return (self._grid(self._width(), 1, 0), self._grid(self._width(), 1, 0))

    # Yes/No decision component
    def ui_yes(self) -> Coords:
        assert self.layout_type is LayoutType.Delizia
        return self.grid34(2, 2)

    def ui_no(self) -> Coords:
        assert self.layout_type is LayoutType.Delizia
        return self.grid34(0, 2)

    # +/- buttons in number input component
    def number_input_minus(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return (self._left(), self._grid(self._height(), 5, 1))
        elif self.layout_type is LayoutType.Delizia:
            return (self._left(), self._grid(self._height(), 5, 3))
        else:
            raise ValueError("Wrong layout type")

    def number_input_plus(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return (self._right(), self._grid(self._height(), 5, 1))
        elif self.layout_type is LayoutType.Delizia:
            return (self._right(), self._grid(self._height(), 5, 3))
        else:
            raise ValueError("Wrong layout type")

    def word_count_all_word(self, word_count: int) -> Coords:
        assert word_count in (12, 18, 20, 24, 33)
        if self.layout_type is LayoutType.Bolt:
            coords_map = {
                12: self.grid34(0, 2),
                18: self.grid34(1, 2),
                20: self.grid34(2, 2),
                24: self.grid34(1, 3),
                33: self.grid34(2, 3),
            }
        elif self.layout_type is LayoutType.Delizia:
            coords_map = {
                12: self.grid34(0, 1),
                18: self.grid34(2, 1),
                20: self.grid34(0, 2),
                24: self.grid34(2, 2),
                33: self.grid34(2, 3),
            }
        else:
            raise ValueError("Wrong layout type")

        return coords_map[word_count]

    def word_count_all_cancel(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return self.grid34(0, 3)

        elif self.layout_type is LayoutType.Delizia:
            return self.grid34(0, 3)

        else:
            raise ValueError("Wrong layout type")

    def word_count_repeated_word(self, word_count: int) -> Coords:
        assert word_count in (20, 33)
        if self.layout_type is LayoutType.Bolt:
            coords_map = {
                20: self.grid34(1, 2),
                33: self.grid34(2, 2),
            }
        elif self.layout_type is LayoutType.Delizia:
            coords_map = {
                20: self.grid34(0, 1),
                33: self.grid34(2, 1),
            }
        else:
            raise ValueError("Wrong layout type")

        return coords_map[word_count]

    def word_count_repeated_cancel(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return self.grid34(0, 2)

        elif self.layout_type is LayoutType.Delizia:
            return self.grid34(0, 3)

        else:
            raise ValueError("Wrong layout type")

    # select word component buttons
    def word_check_words(self) -> "list[Coords]":
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return [
                (self._mid(), self._grid(self._height(), 5, 2)),
                (self._mid(), self._grid(self._height(), 5, 3)),
                (self._mid(), self._grid(self._height(), 5, 4)),
            ]
        else:
            raise ValueError("Wrong layout type")

    # vertical menu buttons
    def vertical_menu_items(self) -> "list[Coords]":
        assert self.layout_type is LayoutType.Delizia

        return [
            (self._mid(), self._grid(self._height(), 4, 1)),
            (self._mid(), self._grid(self._height(), 4, 2)),
            (self._mid(), self._grid(self._height(), 4, 3)),
        ]

    # Pin/passphrase keyboards
    def pin_passphrase_index(self, idx: int) -> Coords:
        assert idx < 10
        if idx == 9:
            idx = 10  # last digit is in the middle
        return self.pin_passphrase_grid(idx % 3, idx // 3)

    def pin_passphrase_grid(self, x: int, y: int) -> Coords:
        assert x < 3, y < 4
        y += 1  # first line is empty
        return self._grid35(x, y)

    # PIN/passphrase input
    def pin_passphrase_input(self) -> Coords:
        return (self._mid(), self._top())

    def pin_passphrase_erase(self) -> Coords:
        return self.pin_passphrase_grid(0, 3)

    def passphrase_confirm(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return self.pin_passphrase_grid(2, 3)
        elif self.layout_type is LayoutType.Delizia:
            return (215, 25)
        else:
            raise ValueError("Wrong layout type")

    def pin_confirm(self) -> Coords:
        return self.pin_passphrase_grid(2, 3)

    # Mnemonic keyboard
    def mnemonic_from_index(self, idx: int) -> Coords:
        return self.mnemonic_grid(idx)

    def mnemonic_grid(self, idx: int) -> Coords:
        assert idx < 9
        grid_x = idx % 3
        grid_y = idx // 3 + 1  # first line is empty
        return self.grid34(grid_x, grid_y)

    def mnemonic_erase(self) -> Coords:
        return (self._left(), self._top())

    def mnemonic_confirm(self) -> Coords:
        return (self._mid(), self._top())


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


class ButtonActions:
    def __init__(self, layout_type: LayoutType):
        self.buttons = ScreenButtons(layout_type)

    def passphrase(self, char: str) -> Tuple[Coords, int]:
        choices = get_passphrase_choices(char)
        idx = next(i for i, letters in enumerate(choices) if char in letters)
        click_amount = choices[idx].index(char) + 1
        return self.buttons.pin_passphrase_index(idx), click_amount

    def type_word(self, word: str, is_slip39: bool = False) -> Iterator[Coords]:
        if is_slip39:
            yield from self._type_word_slip39(word)
        else:
            yield from self._type_word_bip39(word)

    def _type_word_slip39(self, word: str) -> Iterator[Coords]:
        for l in word:
            idx = next(
                i for i, letters in enumerate(BUTTON_LETTERS_SLIP39) if l in letters
            )
            yield self.buttons.mnemonic_from_index(idx)

    def _type_word_bip39(self, word: str) -> Iterator[Coords]:
        coords_prev: Coords | None = None
        for letter in word:
            time.sleep(0.1)  # not being so quick to miss something
            coords, amount = self._letter_coords_and_amount(letter)
            # If the button is the same as for the previous letter,
            # waiting a second before pressing it again.
            if coords == coords_prev:
                time.sleep(1.1)
            coords_prev = coords
            for _ in range(amount):
                yield coords

    def _letter_coords_and_amount(self, letter: str) -> Tuple[Coords, int]:
        idx = next(
            i for i, letters in enumerate(BUTTON_LETTERS_BIP39) if letter in letters
        )
        click_amount = BUTTON_LETTERS_BIP39[idx].index(letter) + 1
        return self.buttons.mnemonic_from_index(idx), click_amount
