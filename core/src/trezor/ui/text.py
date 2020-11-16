from micropython import const

from trezor import ui

if False:
    from typing import List, Union, Tuple, Iterator, Iterable, Optional

TEXT_HEADER_HEIGHT = const(48)
TEXT_LINE_HEIGHT = const(26)
TEXT_LINE_HEIGHT_HALF = const(13)
TEXT_MARGIN_LEFT = const(14)
TEXT_MAX_LINES = const(5)

# needs to be different from all colors and font ids
BR = const(-256)
BR_HALF = const(-257)

_FONTS = (ui.NORMAL, ui.BOLD, ui.MONO)

if False:
    TextContent = Union[str, int]
    BreakIndex = Tuple[
        int, int, Optional[str]
    ]  # "word" index, char index, split marker


def next_sentinel(
    iterator: Iterator[BreakIndex], sentinel: BreakIndex = (65535, 0, None)
) -> BreakIndex:
    try:
        return next(iterator)
    except StopIteration:
        return sentinel


def measure_line(
    string: str,
    string_offset: int = 0,
    line_width: int = ui.WIDTH,
    font: int = ui.NORMAL,
    splitw: int = 0,
    break_spaces: bool = False,
) -> Tuple[int, int]:
    width = 0
    i_space = None
    i_split = None

    for i in range(0, len(string) - string_offset):
        if break_spaces and string[string_offset + i] == " ":
            i_space = i

        width += ui.display.text_width(string[string_offset + i], font)
        if width + splitw < line_width:
            i_split = i
        if width >= line_width:
            break
    else:
        return i + 1, width  # rest fits

    if i_space is not None:
        return i_space + 1, width  # split at space
    elif i_split is not None:
        return i_split + 1, width + splitw  # split word
    else:
        return 0, 0  # not a single char


def break_lines(
    words: List[TextContent],
    new_lines: bool,
    max_lines: int,
    font: int = ui.NORMAL,
    offset_x: int = TEXT_MARGIN_LEFT,
    offset_y: int = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT,
    offset_x_max: int = ui.WIDTH,
    break_spaces: bool = False,
) -> List[BreakIndex]:
    # initial rendering state
    INITIAL_OFFSET_X = offset_x
    offset_y_max = TEXT_HEADER_HEIGHT + (TEXT_LINE_HEIGHT * max_lines)

    # sizes of common glyphs
    DASH = ui.display.text_width("-", ui.BOLD)
    ELLIPSIS = ui.display.text_width("...", ui.BOLD)

    result = []  # type: List[BreakIndex]
    word_index = -1
    for word in words:
        word_index += 1

        has_next_word = word_index < len(words) - 1

        if isinstance(word, int):
            if word is BR:
                # line break
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT
                result.append((word_index, 0, None))
            elif word is BR_HALF:
                # half-line break
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT_HALF
            elif word in _FONTS:
                # change of font style
                font = word
            continue

        width = ui.display.text_width(word, font)
        char_index = 0

        while offset_x + width > offset_x_max or (
            has_next_word and offset_y >= offset_y_max
        ):
            beginning_of_line = offset_x == INITIAL_OFFSET_X
            last_line = offset_y >= offset_y_max
            word_fits_in_one_line = width < (offset_x_max - INITIAL_OFFSET_X)

            # avoid breaking the word if it fits on the next line
            if word_fits_in_one_line and not beginning_of_line and not last_line:
                result.append((word_index, 0, None))
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT
                break

            nchars, width = measure_line(
                word,
                char_index,
                offset_x_max - offset_x,
                font,
                ELLIPSIS if last_line else DASH,
                break_spaces,
            )

            # avoid rendering "-" with empty span
            if nchars == 0 and not last_line and not beginning_of_line:
                result.append((word_index, char_index, None))
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT
                width = ui.display.text_width(word, font, char_index)
                continue

            # break up word
            if break_spaces and word[char_index + nchars - 1] == " ":
                split = None
            elif last_line:
                split = "..."
            else:
                split = "-"
            result.append((word_index, char_index + nchars, split))
            if last_line:
                return result
            offset_x = INITIAL_OFFSET_X
            offset_y += TEXT_LINE_HEIGHT

            # continue with the rest
            char_index += nchars
            width = ui.display.text_width(word, font, char_index)

        if new_lines and has_next_word:
            # line break
            result.append((word_index, len(word), None))
            offset_x = INITIAL_OFFSET_X
            offset_y += TEXT_LINE_HEIGHT
        else:
            # shift cursor
            offset_x += width
            offset_x += ui.display.text_width(" ", font)

    return result


def render_text(
    words: List[TextContent],
    new_lines: bool,
    max_lines: int,
    breaks: Iterable[BreakIndex] = (),
    font: int = ui.NORMAL,
    fg: int = ui.FG,
    bg: int = ui.BG,
    offset_x: int = TEXT_MARGIN_LEFT,
    offset_y: int = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT,
    line_offset: int = 0,
) -> None:
    # initial rendering state
    INITIAL_OFFSET_X = offset_x
    offset_y_max = TEXT_HEADER_HEIGHT + (TEXT_LINE_HEIGHT * max_lines)

    line_no = 0
    breaks_it = iter(breaks)
    break_word_index, break_char_index, break_split = next_sentinel(breaks_it)

    word_index = -1
    for word in words:
        word_index += 1

        if isinstance(word, int):
            if word is BR or word is BR_HALF:
                # line break or half-line break
                if offset_y > offset_y_max and line_no >= line_offset:
                    ui.display.text(offset_x, offset_y, "...", ui.BOLD, ui.GREY, bg)
                    return
                if word is BR:
                    assert break_word_index == word_index
                    break_word_index, break_char_index, break_split = next_sentinel(
                        breaks_it
                    )
                    if line_no >= line_offset:
                        offset_x = INITIAL_OFFSET_X
                        offset_y += TEXT_LINE_HEIGHT
                    line_no += 1
                else:
                    offset_x = INITIAL_OFFSET_X
                    offset_y += TEXT_LINE_HEIGHT_HALF
            elif word in _FONTS:
                # change of font style
                font = word
            else:
                # change of foreground color
                fg = word
            continue

        assert break_word_index >= word_index

        begin = 0
        while break_word_index == word_index:
            span_len = break_char_index - begin
            width = ui.display.text_width(word, font, begin, span_len)

            if line_no >= line_offset:
                ui.display.text(offset_x, offset_y, word, font, fg, bg, begin, span_len)
                if break_split is not None:
                    ui.display.text(
                        offset_x + width, offset_y, break_split, ui.BOLD, ui.GREY, bg
                    )

            if offset_y >= offset_y_max:
                return
            begin = break_char_index
            break_word_index, break_char_index, break_split = next_sentinel(breaks_it)
            if line_no >= line_offset:
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT
            line_no += 1

        if begin == len(word):
            continue

        # render word
        if line_no >= line_offset:
            ui.display.text(offset_x, offset_y, word, font, fg, bg, begin)
            offset_x += ui.display.text_width(word, font, begin)
            offset_x += ui.display.text_width(" ", font)


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
        self.content = []  # type: List[TextContent]
        self.breaks = None  # type: Optional[List[BreakIndex]]
        self.line_offset = 0
        self.repaint = True

    def normal(self, *content: TextContent) -> None:
        self.content.append(ui.NORMAL)
        self.content.extend(content)
        self.breaks = None

    def bold(self, *content: TextContent) -> None:
        self.content.append(ui.BOLD)
        self.content.extend(content)
        self.breaks = None

    def mono(self, *content: TextContent) -> None:
        self.content.append(ui.MONO)
        self.content.extend(content)
        self.breaks = None

    def br(self) -> None:
        self.content.append(BR)
        self.breaks = None

    def br_half(self) -> None:
        self.content.append(BR_HALF)
        self.breaks = None

    def on_render(self) -> None:
        if self.repaint:
            ui.header(
                self.header_text,
                self.header_icon,
                ui.TITLE_GREY,
                ui.BG,
                self.icon_color,
            )
            if self.breaks is None:
                self.breaks = break_lines(self.content, self.new_lines, self.max_lines)
            render_text(
                self.content,
                self.new_lines,
                self.max_lines,
                breaks=self.breaks,
                line_offset=self.line_offset,
            )
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
            ui.display.bar(ax, ay, aw, ah, ui.BG)
            tx = ax + aw // 2
            ty = ay + ah // 2 + 8
            if align is LABEL_LEFT:
                ui.display.text(tx, ty, self.content, self.style, ui.FG, ui.BG)
            elif align is LABEL_CENTER:
                ui.display.text_center(tx, ty, self.content, self.style, ui.FG, ui.BG)
            elif align is LABEL_RIGHT:
                ui.display.text_right(tx, ty, self.content, self.style, ui.FG, ui.BG)
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
