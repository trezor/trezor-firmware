from trezor import ui
from trezor.ui import display, style

from ..common.text import BR, BR_HALF, TextBase  # noqa: F401

if False:
    from typing import List, Optional
    from ..common.text import TextContent


def header(title: str, fg: int = style.FG, bg: int = style.BG) -> None:
    display.text(0, 7, title, ui.BOLD, fg, bg)
    for x in range(0, ui.WIDTH, 2):
        display.bar(x, 9, 1, 1, ui.FG)


class Text(TextBase):
    TEXT_HEADER_HEIGHT = 13
    TEXT_LINE_HEIGHT = 9
    TEXT_LINE_HEIGHT_HALF = 4
    TEXT_MARGIN_LEFT = 0
    TEXT_MAX_LINES = 4

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
        self.repaint = True

    def on_render(self) -> None:
        if self.repaint:
            if self.header_text:
                header(
                    self.header_text, ui.TITLE_GREY, ui.BG,
                )
                self.render_text(self.content, self.new_lines, self.max_lines)
            else:
                self.render_text(
                    self.content,
                    self.new_lines,
                    self.max_lines,
                    offset_y=self.NO_HEADER_TEXT_Y,
                )
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            lines = [w for w in self.content if isinstance(w, str)]
            header_text = [self.header_text] if self.header_text is not None else []
            return header_text + lines[: self.max_lines]
