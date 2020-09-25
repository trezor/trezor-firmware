from micropython import const

from trezor import ui, utils

if False:
    from typing import List, Union, Dict

    TextContent = Union[str, int]
    ListsArg = Dict[str, List[str]]

# needs to be different from all colors and font ids
BR = const(-256)
BR_HALF = const(-257)


# FIXME: ugly & had to get rid of const()
if utils.MODEL == "1":
    TEXT_HEADER_HEIGHT = 13
    TEXT_LINE_HEIGHT = 9
    TEXT_LINE_HEIGHT_HALF = 4
    TEXT_MARGIN_LEFT = 0
    TEXT_MAX_LINES = 4
elif utils.MODEL == "T":
    TEXT_HEADER_HEIGHT = 48
    TEXT_LINE_HEIGHT = 26
    TEXT_LINE_HEIGHT_HALF = 13
    TEXT_MARGIN_LEFT = 14
    TEXT_MAX_LINES = 5
else:
    raise ValueError("Unknown Trezor model")


def render_text(
    words: List[TextContent],
    new_lines: bool,
    max_lines: int,
    font: int = ui.NORMAL,
    fg: int = ui.FG,
    bg: int = ui.BG,
    offset_x: int = TEXT_MARGIN_LEFT,
    offset_y: int = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT,
    offset_x_max: int = ui.WIDTH,
) -> None:
    # initial rendering state
    INITIAL_OFFSET_X = offset_x
    offset_y_max = TEXT_HEADER_HEIGHT + (TEXT_LINE_HEIGHT * max_lines)

    FONTS = (ui.NORMAL, ui.BOLD, ui.MONO)

    # sizes of common glyphs
    SPACE = ui.display.text_width(" ", font)
    DASH = ui.display.text_width("-", ui.BOLD)
    ELLIPSIS = ui.display.text_width("...", ui.BOLD)

    for word_index, word in enumerate(words):
        has_next_word = word_index < len(words) - 1

        if isinstance(word, int):
            if word is BR or word is BR_HALF:
                # line break or half-line break
                if offset_y > offset_y_max:
                    ui.display.text(offset_x, offset_y, "...", ui.BOLD, ui.GREY, bg)
                    return
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT if word is BR else TEXT_LINE_HEIGHT_HALF
            elif word in FONTS:
                # change of font style
                font = word
            else:
                # change of foreground color
                fg = word
            continue

        width = ui.display.text_width(word, font)

        while offset_x + width > offset_x_max or (
            has_next_word and offset_y >= offset_y_max
        ):
            beginning_of_line = offset_x == INITIAL_OFFSET_X
            word_fits_in_one_line = width < (offset_x_max - INITIAL_OFFSET_X)
            if (
                offset_y < offset_y_max
                and word_fits_in_one_line
                and not beginning_of_line
            ):
                # line break
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT
                break
            # word split
            if offset_y < offset_y_max:
                split = "-"
                splitw = DASH
            else:
                split = "..."
                splitw = ELLIPSIS
            # find span that fits
            for index in range(len(word) - 1, 0, -1):
                letter = word[index]
                width -= ui.display.text_width(letter, font)
                if offset_x + width + splitw < offset_x_max:
                    break
            else:
                index = 0
            span = word[:index]
            # render word span
            ui.display.text(offset_x, offset_y, span, font, fg, bg)
            ui.display.text(offset_x + width, offset_y, split, ui.BOLD, ui.GREY, bg)
            # line break
            if offset_y >= offset_y_max:
                return
            offset_x = INITIAL_OFFSET_X
            offset_y += TEXT_LINE_HEIGHT
            # continue with the rest
            word = word[index:]
            width = ui.display.text_width(word, font)

        # render word
        ui.display.text(offset_x, offset_y, word, font, fg, bg)

        if new_lines and has_next_word:
            # line break
            if offset_y >= offset_y_max:
                ui.display.text(offset_x, offset_y, "...", ui.BOLD, ui.GREY, bg)
                return
            offset_x = INITIAL_OFFSET_X
            offset_y += TEXT_LINE_HEIGHT
        else:
            # shift cursor
            offset_x += width
            offset_x += SPACE


# confirm.py
CONFIRMED = object()
CANCELLED = object()
INFO = object()
