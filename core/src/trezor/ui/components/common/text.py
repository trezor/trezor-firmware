from micropython import const

from trezor import ui

from ...constants import (
    TEXT_HEADER_HEIGHT,
    TEXT_LINE_HEIGHT,
    TEXT_LINE_HEIGHT_HALF,
    TEXT_MARGIN_LEFT,
    TEXT_MAX_LINES,
)

if False:
    from typing import Any, List, Optional, Union

    TextContent = Union[str, int]

# needs to be different from all colors and font ids
BR = const(-256)
BR_HALF = const(-257)

_FONTS = (ui.NORMAL, ui.BOLD, ui.MONO)

DASH_WIDTH = ui.display.text_width("-", ui.BOLD)


class Span:
    def __init__(
        self,
        string: str = "",
        start: int = 0,
        font: int = ui.NORMAL,
        line_width: int = ui.WIDTH - TEXT_MARGIN_LEFT,
        offset_x: int = 0,
        break_words: bool = False,
    ) -> None:
        self.reset(string, start, font, line_width, offset_x, break_words)

    def reset(
        self,
        string: str,
        start: int,
        font: int,
        line_width: int = ui.WIDTH - TEXT_MARGIN_LEFT,
        offset_x: int = 0,
        break_words: bool = False,
    ) -> None:
        self.string = string
        self.start = start
        self.font = font
        self.line_width = line_width
        self.offset_x = offset_x
        self.break_words = break_words

        self.length = 0
        self.width = 0
        self.word_break = False
        self.advance_whitespace = False

    def count_lines(self) -> int:
        """Get a number of lines in the specified string.

        Should be used with a cleanly reset span. Leaves the span in the final position.
        """
        n_lines = 0
        while self.next_line():
            n_lines += 1
        # deal with trailing newlines: if the final span does not have any content,
        # do not count it
        if self.length > 0:
            n_lines += 1
        return n_lines

    def has_more_content(self) -> bool:
        """Look ahead to check if there is more content after the current span is
        consumed.
        """
        start = self.start + self.length
        if self.advance_whitespace:
            start += 1
        return start < len(self.string)

    def next_line(self) -> bool:
        """Advance the span to point to contents of the next line.

        Returns True if the renderer should make newline afterwards, False if this is
        the end of the text.

        Within the renderer, we use this as:

        >>> while span.next_line():
        >>>     render_the_line(span)
        >>>     go_to_next_line()
        >>> render_the_line(span)  # final line without linebreak

        This is unsuitable for other uses however. To count lines (as in
        `apps.common.layout.paginate_text`), use instead:

        >>> while span.has_more_content():
        >>>     span.next_line()
        """
        # We are making copies of most class variables so that the lookup is faster.
        # This also allows us to pick defaults independently of the current status
        string = self.string
        start = self.start + self.length
        line_width = self.line_width - self.offset_x
        break_words = self.break_words
        font = self.font

        self.offset_x = 0
        width = 0
        result_width = 0
        length = 0

        if start >= len(string):
            return False

        # advance over the left-over whitespace character from last time
        if self.advance_whitespace:
            start += 1

        word_break = True
        advance_whitespace = False
        for i in range(len(string) - start):
            nextchar_width = ui.display.text_width(string[start + i], font)

            if string[start + i] in " \n":
                word_break = False
                length = i  # break is _before_ the whitespace
                advance_whitespace = True
                result_width = width
                if string[start + i] == "\n":
                    # do not continue over newline
                    break

            elif width + nextchar_width > line_width:
                # this char would overflow the line. end loop, use last result
                break

            elif (
                break_words or word_break
            ) and width + nextchar_width + DASH_WIDTH <= line_width:
                # Trying a possible break in the middle of a word.
                # We can do this if:
                # - we haven't found a space yet (word_break is still True) -- if a word
                #   doesn't fit on a single line, this will place a break in it
                # - we are allowed to break words (break_words is True)
                # AND the current character and a word-break dash will fit on the line.
                result_width = width + nextchar_width
                length = i + 1  # break is _after_ current character
                advance_whitespace = False
                word_break = True

            width += nextchar_width

        else:
            # whole string (from offset) fits
            word_break = False
            advance_whitespace = False
            result_width = width
            length = len(string) - start

        self.start = start
        self.length = length
        self.width = result_width
        self.word_break = word_break
        self.advance_whitespace = advance_whitespace
        return start + length < len(string)


_WORKING_SPAN = Span()


def render_text(
    items: List[TextContent],
    new_lines: bool,
    max_lines: int,
    font: int = ui.NORMAL,
    fg: int = ui.FG,
    bg: int = ui.BG,
    offset_x: int = TEXT_MARGIN_LEFT,
    offset_y: int = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT,
    line_width: int = ui.WIDTH - TEXT_MARGIN_LEFT,
    item_offset: int = 0,
    char_offset: int = 0,
    break_words: bool = False,
    render_page_overflow: bool = True,
) -> None:
    """Render a sequence of items on screen.

    The items can either be strings, or rendering instructions specified as ints.
    They can change font, insert an explicit linebreak, or change color of the following
    text.

    If `new_lines` is true, a linebreak is rendered after every string. In effect, the
    following calls are equivalent:

    >>> render_text(["hello", "world"], new_lines=True)
    >>> render_text(["hello\nworld"], new_lines=False)

    TODO, we should get rid of all cases that use `new_lines=True`

    If the rendered text ends up longer than `max_lines`, a trailing "..." is rendered
    at end. This indicates to the user that the full contents have not been shown.
    It is possible to override this behavior via `render_page_overflow` argument --
    if false, the trailing "..." is not shown. This is useful when the rendered text is
    in fact paginated.

    `font` specifies the default font, but that can be overriden by font instructions
    in `items`.
    `fg` specifies default foreground color, which can also be overriden by instructions
    in `items`.
    `bg` specifies background color. This cannot be overriden.

    `offset_x` and `offset_y` specify starting XY position of the text bounding box.
    `line_width` specifies width of the bounding box. Height of the bounding box is
    calculated as `max_lines * TEXT_LINE_HEIGHT`.

    `item_offset` and `char_offset` must be specified together. Item offset specifies
    the first element of `items` which should be considered, and char offset specifies
    the first character of the indicated item which should be considered.
    The purpose is to allow rendering different "pages" of text, using the same `items`
    argument (slicing the list could be expensive in terms of memory).

    If `break_words` is false (default), linebreaks will only be rendered (a) at
    whitespace, or (b) in case a word does not fit on a single line. If true, whitespace
    is ignored and linebreaks are inserted after the last character that fits.
    """
    # initial rendering state
    INITIAL_OFFSET_X = offset_x
    offset_y_max = TEXT_HEADER_HEIGHT + (TEXT_LINE_HEIGHT * max_lines)
    span = _WORKING_SPAN

    # scan through up to item_offset so that the current font & color is up to date
    for item_index in range(item_offset):
        item = items[item_index]
        if isinstance(item, int):
            if item is BR or item is BR_HALF:
                # do nothing
                pass
            elif item in _FONTS:
                font = item
            else:
                fg = item

    SPACE = ui.display.text_width(" ", font)

    for item_index in range(item_offset, len(items)):
        # load current item
        item = items[item_index]

        if isinstance(item, int):
            if item is BR or item is BR_HALF:
                # line break or half-line break
                if offset_y > offset_y_max:
                    if render_page_overflow:
                        ui.display.text(offset_x, offset_y, "...", ui.BOLD, ui.GREY, bg)
                    return
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT if item is BR else TEXT_LINE_HEIGHT_HALF
            elif item in _FONTS:
                # change of font style
                font = item
                SPACE = ui.display.text_width(" ", font)
            else:
                # change of foreground color
                fg = item
            continue

        # XXX hack:
        # if the upcoming word does not fit on this line but fits on the following,
        # render it after a linebreak
        item_width = ui.display.text_width(item, font)
        if (
            item_width <= line_width
            and item_width + offset_x - INITIAL_OFFSET_X > line_width
            and "\n" not in item
        ):
            offset_y += TEXT_LINE_HEIGHT
            ui.display.text(INITIAL_OFFSET_X, offset_y, item, font, fg, bg)
            offset_x = INITIAL_OFFSET_X + item_width + SPACE
            continue

        span.reset(
            item,
            char_offset,
            font,
            line_width=line_width,
            offset_x=offset_x - INITIAL_OFFSET_X,
            break_words=break_words,
        )
        char_offset = 0
        while span.next_line():
            ui.display.text(
                offset_x, offset_y, item, font, fg, bg, span.start, span.length
            )
            end_of_page = offset_y >= offset_y_max
            have_more_content = span.has_more_content() or item_index < len(items) - 1

            if end_of_page and have_more_content and render_page_overflow:
                ui.display.text(
                    offset_x + span.width, offset_y, "...", ui.BOLD, ui.GREY, bg
                )
            elif span.word_break:
                ui.display.text(
                    offset_x + span.width, offset_y, "-", ui.BOLD, ui.GREY, bg
                )

            if end_of_page:
                return

            offset_x = INITIAL_OFFSET_X
            offset_y += TEXT_LINE_HEIGHT

        # render last chunk
        ui.display.text(offset_x, offset_y, item, font, fg, bg, span.start, span.length)

        if new_lines:
            offset_x = INITIAL_OFFSET_X
            offset_y += TEXT_LINE_HEIGHT
        elif span.width > 0:
            # only advance cursor if we actually rendered anything
            offset_x += span.width + SPACE


if __debug__:

    class DisplayMock:
        """Mock Display class that stores rendered text in an array.

        Used to extract data for unit tests.
        """

        def __init__(self) -> None:
            self.screen_contents: List[str] = []
            self.orig_display = ui.display

        def __getattr__(self, key: str) -> Any:
            return getattr(self.orig_display, key)

        def __enter__(self) -> None:
            ui.display = self  # type: ignore

        def __exit__(self, exc: Any, exc_type: Any, tb: Any) -> None:
            ui.display = self.orig_display

        def text(
            self,
            offset_x: int,
            offset_y: int,
            string: str,
            font: int,
            fg: int,
            bg: int,
            start: int = 0,
            length: Optional[int] = None,
        ) -> None:
            if length is None:
                length = len(string) - start
            self.screen_contents.append(string[start : start + length])


class TextBase(ui.Component):
    def __init__(
        self,
        header_text: str,
        header_icon: str = ui.ICON_DEFAULT,
        icon_color: int = ui.ORANGE_ICON,
        max_lines: int = TEXT_MAX_LINES,
        new_lines: bool = True,
        break_words: bool = False,
        render_page_overflow: bool = True,
        content_offset: int = 0,
        char_offset: int = 0,
        line_width: int = ui.WIDTH - TEXT_MARGIN_LEFT,
    ):
        super().__init__()
        self.header_text = header_text
        self.header_icon = header_icon
        self.icon_color = icon_color
        self.max_lines = max_lines
        self.new_lines = new_lines
        self.break_words = break_words
        self.render_page_overflow = render_page_overflow
        self.content: List[TextContent] = []
        self.content_offset = content_offset
        self.char_offset = char_offset
        self.line_width = line_width

    def normal(self, *content: TextContent) -> None:
        self.content.append(ui.NORMAL)
        self.content.extend(content)

    def bold(self, *content: TextContent) -> None:
        self.content.append(ui.BOLD)
        self.content.extend(content)

    def mono(self, *content: TextContent) -> None:
        self.content.append(ui.MONO)
        self.content.extend(content)

    def br(self) -> None:
        self.content.append(BR)

    def br_half(self) -> None:
        self.content.append(BR_HALF)

    def on_render(self) -> None:
        pass

    if __debug__:

        def read_content(self) -> List[str]:
            display_mock = DisplayMock()
            should_repaint = self.repaint
            try:
                with display_mock:
                    self.repaint = True
                    self.on_render()
            finally:
                self.repaint = should_repaint
            return [self.header_text] + display_mock.screen_contents


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
        super().__init__()
        self.area = area
        self.content = content
        self.align = align
        self.style = style

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
