from micropython import const

from trezor import ui

if False:
    from typing import List, Union

TEXT_HEADER_HEIGHT = const(48)
TEXT_LINE_HEIGHT = const(26)
TEXT_LINE_HEIGHT_HALF = const(13)
TEXT_MARGIN_LEFT = const(14)
TEXT_MAX_LINES = const(5)

# needs to be different from all colors and font ids
BR = const(-256)
BR_HALF = const(-257)

if False:
    TextContent = Union[str, int]


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
    offset_y_max = offset_y * max_lines

    FONTS = (ui.NORMAL, ui.BOLD, ui.MONO, ui.MONO_BOLD)

    # sizes of common glyphs
    SPACE = ui.display.text_width(" ", font)
    DASH = ui.display.text_width("-", ui.BOLD)
    ELLIPSIS = ui.display.text_width("...", ui.BOLD)

    for word_index, word in enumerate(words):
        has_next_word = word_index < len(words) - 1

        if isinstance(word, int):
            if word is BR or word is BR_HALF:
                # line break or half-line break
                if offset_y >= offset_y_max:
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


class Text(ui.Component):
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
        self.content = []  # type: List[Union[str, int]]
        self.repaint = True

    def normal(self, *content: TextContent) -> None:
        self.content.append(ui.NORMAL)
        self.content.extend(content)

    def bold(self, *content: TextContent) -> None:
        self.content.append(ui.BOLD)
        self.content.extend(content)

    def mono(self, *content: TextContent) -> None:
        self.content.append(ui.MONO)
        self.content.extend(content)

    def mono_bold(self, *content: TextContent) -> None:
        self.content.append(ui.MONO_BOLD)
        self.content.extend(content)

    def br(self) -> None:
        self.content.append(BR)

    def br_half(self) -> None:
        self.content.append(BR_HALF)

    def on_render(self) -> None:
        if self.repaint:
            ui.header(
                self.header_text,
                self.header_icon,
                ui.TITLE_GREY,
                ui.BG,
                self.icon_color,
            )
            render_text(self.content, self.new_lines, self.max_lines)
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            lines = [w for w in self.content if isinstance(w, str)]
            return [self.header_text] + lines[: self.max_lines]


LABEL_LEFT = const(0)
LABEL_CENTER = const(1)
LABEL_RIGHT = const(2)


class Label(ui.Component):
    def __init__(
        self,
        area: ui.Area,
        content: str,
        align: int = LABEL_LEFT,
        style: int = ui.NORMAL,
    ) -> None:
        self.area = area
        self.content = content
        self.align = align
        self.style = style
        self.repaint = True

    def on_render(self) -> None:
        if self.repaint:
            align = self.align
            ax, ay, aw, ah = self.area
            tx = ax + aw // 2
            ty = ay + ah // 2 + 8
            if align is LABEL_LEFT:
                ui.display.text(tx, ty, self.content, self.style, ui.FG, ui.BG, aw)
            elif align is LABEL_CENTER:
                ui.display.text_center(
                    tx, ty, self.content, self.style, ui.FG, ui.BG, aw
                )
            elif align is LABEL_RIGHT:
                ui.display.text_right(
                    tx, ty, self.content, self.style, ui.FG, ui.BG, aw
                )
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            return [self.content]


def text_center_trim_left(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[-i:], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[-text_length:], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
    x += ELLIPSIS_WIDTH
    ui.display.text(x, y, text[-text_length:], font, ui.FG, ui.BG)


def text_center_trim_right(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[:i], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[:text_length], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, text[:text_length], font, ui.FG, ui.BG)
    x += text_width
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
