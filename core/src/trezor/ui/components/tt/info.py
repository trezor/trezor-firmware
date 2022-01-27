from typing import TYPE_CHECKING

from trezor import loop, res, ui

from ...constants import TEXT_LINE_HEIGHT, TEXT_MARGIN_LEFT
from .button import Button, ButtonConfirm
from .confirm import CONFIRMED
from .text import render_text

if TYPE_CHECKING:
    from .button import ButtonContent

    InfoConfirmStyleType = type["DefaultInfoConfirm"]


class DefaultInfoConfirm:

    fg_color = ui.LIGHT_GREY
    bg_color = ui.BLACKISH

    class button(ButtonConfirm):
        class normal(ButtonConfirm.normal):
            border_color = ui.BLACKISH

        class disabled(ButtonConfirm.disabled):
            border_color = ui.BLACKISH


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
        self.text = [text]
        self.style = style
        panel_area = ui.grid(0, n_x=1, n_y=1)
        self.panel_area = panel_area
        confirm_area = ui.grid(4, n_x=1)
        self.confirm = Button(confirm_area, confirm, style.button)
        self.confirm.on_click = self.on_confirm

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
                line_width=w - TEXT_MARGIN_LEFT,
                fg=fg_color,
                bg=bg_color,
            )

            self.repaint = False

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    if __debug__:

        def read_content(self) -> list[str]:
            return self.text

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
            from apps.debug import confirm_signal

            return super().create_tasks() + (confirm_signal(),)
