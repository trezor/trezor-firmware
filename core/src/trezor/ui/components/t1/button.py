from micropython import const

from trezor import ui
from trezor.ui import display


class ButtonStyleState:
    bg_color = None  # type: int
    fg_color = None  # type: int
    horiz_border = None  # type: bool


if False:
    from typing import Type, List

    ButtonStyleStateType = Type[ButtonStyleState]
    ButtonContent = str


class ButtonStyle:
    normal = None  # type: ButtonStyleStateType
    active = None  # type: ButtonStyleStateType


if False:
    ButtonStyleType = Type[ButtonStyle]


class ButtonWhite(ButtonStyle):
    class normal(ButtonStyleState):
        bg_color = ui.FG
        fg_color = ui.BG
        horiz_border = True

    class active(normal):
        bg_color = ui.BG
        fg_color = ui.FG
        horiz_border = True


class ButtonBlack(ButtonStyle):
    class normal(ButtonWhite.normal):
        bg_color = ui.BG
        fg_color = ui.FG
        horiz_border = False

    class active(ButtonWhite.active):
        bg_color = ui.FG
        fg_color = ui.BG
        horiz_border = False


_BUTTON_Y = ui.HEIGHT - 11
_BUTTON_H = 11

# button states
_INITIAL = const(0)
_PRESSED = const(1)


def _bar_radius1(x: int, y: int, w: int, h: int, color: int) -> None:
    display.bar(x + 1, y, w - 2, h, color)
    display.bar(x, y + 1, 1, h - 2, color)
    display.bar(x + w - 1, y + 1, 1, h - 2, color)


class Button(ui.Component):
    def __init__(
        self,
        is_right: bool,
        content: ButtonContent,
        style: ButtonStyleType = ButtonWhite,
    ) -> None:
        self.text = content
        self.is_right = is_right
        self.normal_style = style.normal
        self.active_style = style.active
        self.state = _INITIAL
        self.repaint = True

    def render_background(self, s: ButtonStyleStateType) -> None:
        text_width = display.text_width(self.text, ui.BOLD)
        if s.horiz_border:
            _bar_radius1(
                ui.WIDTH - text_width - 3 if self.is_right else 0,  # x
                _BUTTON_Y,  # y
                text_width + 3,  # w
                _BUTTON_H,  # h
                s.bg_color,  # fgcolor
            )
        else:
            display.bar(
                ui.WIDTH - text_width + 1 if self.is_right else 0,  # x
                _BUTTON_Y,  # y
                text_width - 1,  # w
                _BUTTON_H,  # h
                s.bg_color,  # fgcolor
            )

    def render_content(self, s: ButtonStyleStateType) -> None:
        h_border = 2 if s.horiz_border else 0
        if self.is_right:
            display.text_right(
                ui.WIDTH - h_border + 1,
                ui.HEIGHT - 2,
                self.text,
                ui.BOLD,
                s.fg_color,
                s.bg_color,
            )
        else:
            display.text(
                h_border, ui.HEIGHT - 2, self.text, ui.BOLD, s.fg_color, s.bg_color
            )

    def on_render(self) -> None:
        if self.repaint:
            if self.state is _INITIAL:
                s = self.normal_style
            elif self.state is _PRESSED:
                s = self.active_style
            self.render_background(s)
            self.render_content(s)
            self.repaint = False

    def _is_hit(self, x: int, y: int) -> bool:
        if y != ui.HEIGHT - 1:
            return False
        if self.is_right:
            return x == ui.WIDTH - 1
        else:
            return x == 0

    def on_touch_start(self, x: int, y: int) -> None:
        if self._is_hit(x, y):
            self.state = _PRESSED
            self.repaint = True
            self.on_press_start()

    def on_touch_end(self, x: int, y: int) -> None:
        state = self.state
        if state is not _INITIAL:
            self.state = _INITIAL
            self.repaint = True
        if self._is_hit(x, y):
            if state is _PRESSED:
                self.on_press_end()
                self.on_click()

    def on_press_start(self) -> None:
        pass

    def on_press_end(self) -> None:
        pass

    def on_click(self) -> None:
        pass

    if __debug__:

        def read_content(self) -> List[str]:
            return ["<Button: {}>".format(self.text)]
