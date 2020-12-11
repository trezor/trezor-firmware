from trezor import res, ui

from ...constants import TEXT_LINE_HEIGHT, TEXT_MARGIN_LEFT
from .button import Button, ButtonConfirm
from .confirm import CONFIRMED
from .text import render_text

if False:
    from typing import Type
    from .button import ButtonContent


class DefaultInfoConfirm:

    fg_color = ui.LIGHT_GREY
    bg_color = ui.BLACKISH

    class button(ButtonConfirm):
        class normal(ButtonConfirm.normal):
            border_color = ui.BLACKISH

        class disabled(ButtonConfirm.disabled):
            border_color = ui.BLACKISH


if False:
    InfoConfirmStyleType = Type[DefaultInfoConfirm]


class InfoConfirm(ui.Layout):
    DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)
    DEFAULT_STYLE = DefaultInfoConfirm

    def __init__(
        self,
        text: str,
        confirm: ButtonContent = DEFAULT_CONFIRM,
        style: InfoConfirmStyleType = DEFAULT_STYLE,
    ) -> None:
        super().__init__()
        self.text = text.split()
        self.style = style
        panel_area = ui.grid(0, n_x=1, n_y=1)
        self.panel_area = panel_area
        confirm_area = ui.grid(4, n_x=1)
        self.confirm = Button(confirm_area, confirm, style.button)
        self.confirm.on_click = self.on_confirm  # type: ignore

    def dispatch(self, event: int, x: int, y: int) -> None:
        if event == ui.RENDER:
            self.on_render()
        self.confirm.dispatch(event, x, y)

    def on_render(self) -> None:
        if self.repaint:
            x, y, w, h = self.panel_area
            fg_color = self.style.fg_color
            bg_color = self.style.bg_color

            # render the background panel
            ui.display.bar_radius(x, y, w, h, bg_color, ui.BG, ui.RADIUS)

            # render the info text
            render_text(
                self.text,
                new_lines=False,
                max_lines=6,
                offset_y=y + TEXT_LINE_HEIGHT,
                offset_x=x + TEXT_MARGIN_LEFT - ui.VIEWX,
                line_width=w,
                fg=fg_color,
                bg=bg_color,
            )

            self.repaint = False

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)
