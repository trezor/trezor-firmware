from trezor import ui
from trezor.ui import display, style

from ..common import BR, BR_HALF, TEXT_LINE_HEIGHT, TEXT_MAX_LINES, render_text

if False:
    from typing import List, Optional
    from ..common import TextContent


NO_HEADER_TEXT_Y = TEXT_LINE_HEIGHT - 2


def header(title: str, fg: int = style.FG, bg: int = style.BG) -> None:
    display.text(0, 7, title, ui.BOLD, fg, bg)
    for x in range(0, ui.WIDTH, 2):
        display.bar(x, 9, 1, 1, ui.FG)


class Text(ui.Component):
    def __init__(
        self,
        header_text: Optional[str] = None,
        max_lines: int = TEXT_MAX_LINES,
        new_lines: bool = True,
    ):
        self.header_text = header_text
        self.max_lines = max_lines
        self.new_lines = new_lines
        self.content = []  # type: List[TextContent]
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

    def br(self) -> None:
        self.content.append(BR)

    def br_half(self) -> None:
        self.content.append(BR_HALF)

    def on_render(self) -> None:
        if self.repaint:
            if self.header_text:
                header(
                    self.header_text, ui.TITLE_GREY, ui.BG,
                )
                render_text(self.content, self.new_lines, self.max_lines)
            else:
                render_text(
                    self.content,
                    self.new_lines,
                    self.max_lines,
                    offset_y=NO_HEADER_TEXT_Y,
                )
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            lines = [w for w in self.content if isinstance(w, str)]
            header_text = [self.header_text] if self.header_text is not None else []
            return header_text + lines[: self.max_lines]
