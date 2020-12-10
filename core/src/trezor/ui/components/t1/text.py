from trezor import ui
from trezor.ui import display, style

from ..common.text import (  # noqa: F401
    BR,
    BR_HALF,
    TEXT_LINE_HEIGHT,
    TEXT_MAX_LINES,
    TextBase,
    render_text,
)

if False:
    from typing import List, Optional
    from ..common.text import TextContent


def header(title: str, fg: int = style.FG, bg: int = style.BG) -> None:
    display.text(0, 7, title, ui.BOLD, fg, bg)
    for x in range(0, ui.WIDTH, 2):
        display.bar(x, 9, 1, 1, ui.FG)


class Text(TextBase):
    NO_HEADER_TEXT_Y = TEXT_LINE_HEIGHT - 2

    def __init__(
        self,
        header_text: Optional[str] = None,
        max_lines: int = TEXT_MAX_LINES,
        new_lines: bool = True,
    ):
        super().__init__()
        self.header_text = header_text
        self.max_lines = max_lines
        self.new_lines = new_lines
        self.content = []  # type: List[TextContent]

    def on_render(self) -> None:
        if self.repaint:
            if self.header_text:
                header(self.header_text, ui.TITLE_GREY, ui.BG)
                render_text(self.content, self.new_lines, self.max_lines)
            else:
                render_text(
                    self.content,
                    self.new_lines,
                    self.max_lines,
                    offset_y=self.NO_HEADER_TEXT_Y,
                )
            self.repaint = False
