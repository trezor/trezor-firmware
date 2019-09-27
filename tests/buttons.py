DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240


def grid(dim, grid_cells, cell):
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

MINUS = (LEFT, grid(DISPLAY_HEIGHT, 5, 2))
PLUS = (RIGHT, grid(DISPLAY_HEIGHT, 5, 2))


BUTTON_LETTERS = ("ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz")


def grid35(x, y):
    return grid(DISPLAY_WIDTH, 3, x), grid(DISPLAY_HEIGHT, 5, y)


def grid34(x, y):
    return grid(DISPLAY_WIDTH, 3, x), grid(DISPLAY_HEIGHT, 5, y)


def type_word(word):
    for l in word:
        idx = next(i for i, letters in enumerate(BUTTON_LETTERS) if l in letters)
        grid_x = idx % 3
        grid_y = idx // 3 + 1  # first line is empty
        yield grid34(grid_x, grid_y)
