from micropython import const

from trezor import ui

TEXT_HEADER_HEIGHT = const(48)
TEXT_LINE_HEIGHT = const(26)
TEXT_MARGIN_LEFT = const(14)
TEXT_MAX_LINES = const(5)

# needs to be different from all colors and font ids
BR = const(-256)


def render_text(words: list, new_lines: bool, max_lines: int) -> None:
    # initial rendering state
    font = ui.NORMAL
    fg = ui.FG
    bg = ui.BG
    offset_x = TEXT_MARGIN_LEFT
    offset_y = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT
    OFFSET_X_MAX = ui.WIDTH
    OFFSET_Y_MAX = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT * max_lines
    FONTS = (ui.NORMAL, ui.BOLD, ui.MONO, ui.MONO_BOLD)

    # sizes of common glyphs
    SPACE = ui.display.text_width(" ", font)
    DASH = ui.display.text_width("-", ui.BOLD)
    ELLIPSIS = ui.display.text_width("...", ui.BOLD)

    for word_index, word in enumerate(words):
        has_next_word = word_index < len(words) - 1

        if isinstance(word, int):
            if word == BR:
                # line break
                if offset_y >= OFFSET_Y_MAX:
                    ui.display.text(offset_x, offset_y, "...", ui.BOLD, ui.GREY, bg)
                    return
                offset_x = TEXT_MARGIN_LEFT
                offset_y += TEXT_LINE_HEIGHT
            elif word in FONTS:
                # change of font style
                font = word
            else:
                # change of foreground color
                fg = word
            continue

        width = ui.display.text_width(word, font)

        while offset_x + width > OFFSET_X_MAX or (
            has_next_word and offset_y >= OFFSET_Y_MAX
        ):
            beginning_of_line = offset_x == TEXT_MARGIN_LEFT
            word_fits_in_one_line = width < (OFFSET_X_MAX - TEXT_MARGIN_LEFT)
            if (
                offset_y < OFFSET_Y_MAX
                and word_fits_in_one_line
                and not beginning_of_line
            ):
                # line break
                offset_x = TEXT_MARGIN_LEFT
                offset_y += TEXT_LINE_HEIGHT
                break
            # word split
            if offset_y < OFFSET_Y_MAX:
                split = "-"
                splitw = DASH
            else:
                split = "..."
                splitw = ELLIPSIS
            # find span that fits
            for index in range(len(word) - 1, 0, -1):
                letter = word[index]
                width -= ui.display.text_width(letter, font)
                if offset_x + width + splitw < OFFSET_X_MAX:
                    break
            else:
                index = 0
            span = word[:index]
            # render word span
            ui.display.text(offset_x, offset_y, span, font, fg, bg)
            ui.display.text(offset_x + width, offset_y, split, ui.BOLD, ui.GREY, bg)
            # line break
            if offset_y >= OFFSET_Y_MAX:
                return
            offset_x = TEXT_MARGIN_LEFT
            offset_y += TEXT_LINE_HEIGHT
            # continue with the rest
            word = word[index:]
            width = ui.display.text_width(word, font)

        # render word
        ui.display.text(offset_x, offset_y, word, font, fg, bg)

        if new_lines and has_next_word:
            # line break
            if offset_y >= OFFSET_Y_MAX:
                ui.display.text(offset_x, offset_y, "...", ui.BOLD, ui.GREY, bg)
                return
            offset_x = TEXT_MARGIN_LEFT
            offset_y += TEXT_LINE_HEIGHT
        else:
            # shift cursor
            offset_x += width
            offset_x += SPACE


class Text(ui.LazyWidget):
    def __init__(
        self,
        header_text: str,
        header_icon: str = ui.ICON_DEFAULT,
        icon_color: int = ui.ORANGE_ICON,
        max_lines: int = TEXT_MAX_LINES,
        new_lines: bool = True,
    ):
        self.header_text = header_text
        self.header_icon = header_icon
        self.icon_color = icon_color
        self.max_lines = max_lines
        self.new_lines = new_lines
        self.content = []

    def normal(self, *content):
        self.content.extend(content)

    def bold(self, *content):
        self.content.append(ui.BOLD)
        self.content.extend(content)
        self.content.append(ui.NORMAL)

    def mono(self, *content):
        self.content.append(ui.MONO)
        self.content.extend(content)
        self.content.append(ui.NORMAL)

    def mono_bold(self, *content):
        self.content.append(ui.MONO_BOLD)
        self.content.extend(content)
        self.content.append(ui.NORMAL)

    def br(self):
        self.content.append(BR)

    def render(self):
        ui.header(
            self.header_text, self.header_icon, ui.TITLE_GREY, ui.BG, self.icon_color
        )
        render_text(self.content, self.new_lines, self.max_lines)
