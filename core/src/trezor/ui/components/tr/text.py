from trezor import res, ui
from trezor.ui import display, style

from ..common.text import TEXT_HEADER_HEIGHT, TEXT_LINE_HEIGHT, TextBase, render_text


def header(
    title: str,
    icon: str = style.ICON_DEFAULT,
    fg: int = style.FG,
    bg: int = style.BG,
    ifg: int = style.GREEN,
) -> None:
    if icon is not None:
        display.icon(2, 2, res.load(icon), ifg, bg)
    display.text(35, 18, title, ui.BOLD, fg, bg)


class Text(TextBase):
    def on_render(self) -> None:
        if self.repaint:
            offset_y = TEXT_LINE_HEIGHT
            if self.header_text is not None:
                header(
                    self.header_text,
                    self.header_icon,
                    ui.TITLE_GREY,
                    ui.BG,
                    self.icon_color,
                )
                offset_y = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT
            render_text(
                self.content,
                self.new_lines,
                self.max_lines,
                item_offset=self.content_offset,
                char_offset=self.char_offset,
                break_words=self.break_words,
                line_width=self.line_width,
                render_page_overflow=self.render_page_overflow,
                offset_y=offset_y,
            )
            self.repaint = False
