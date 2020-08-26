from trezor import ui
from trezor.ui import display, in_area

from ..types import ButtonStyle, ButtonStyleState

if False:
    from typing import Optional
    from ..types import (  # noqa: F401
        ButtonStyleStateType,
        ButtonStyleType,
        ButtonContent,
    )


class ButtonDefault(ButtonStyle):
    class normal(ButtonStyleState):
        bg_color = ui.FG
        fg_color = ui.BG
        text_style = ui.BOLD
        border_color = ui.FG
        radius = 1

    class active(normal):
        bg_color = ui.BG
        fg_color = ui.FG
        text_style = ui.BOLD
        border_color = ui.BG
        radius = 1

    class disabled(normal):
        bg_color = ui.FG
        fg_color = ui.BG
        text_style = ui.NORMAL
        border_color = ui.FG
        radius = 1


class ButtonMono(ButtonDefault):
    class normal(ButtonDefault.normal):
        text_style = ui.MONO

    class active(ButtonDefault.active):
        text_style = ui.MONO

    class disabled(ButtonDefault.disabled):
        text_style = ui.MONO


class ButtonMonoDark(ButtonDefault):
    class normal(ButtonDefault.normal):
        bg_color = ui.BG
        fg_color = ui.FG
        text_style = ui.MONO
        border_color = ui.BG
        radius = 0

    class active(normal):
        bg_color = ui.FG
        fg_color = ui.BG
        text_style = ui.MONO
        border_color = ui.FG
        radius = 0

    class disabled(normal):
        bg_color = ui.BG
        fg_color = ui.FG
        text_style = ui.MONO
        border_color = ui.BG
        radius = 0


class ButtonConfirm(ButtonDefault):
    pass


class ButtonCancel(ButtonDefault):
    class normal(ButtonDefault.normal):
        bg_color = ui.BG
        fg_color = ui.FG
        border_color = ui.BG
        radius = 0

    class active(ButtonDefault.active):
        bg_color = ui.FG
        fg_color = ui.BG
        border_color = ui.FG
        radius = 0

    class disabled(ButtonDefault.disabled):
        bg_color = ui.BG
        fg_color = ui.FG
        border_color = ui.BG
        radius = 0


class ButtonAbort(ButtonDefault):
    pass


class ButtonClear(ButtonCancel):
    pass


class ButtonMonoConfirm(ButtonDefault):
    class normal(ButtonDefault.normal):
        text_style = ui.MONO

    class active(ButtonDefault.active):
        text_style = ui.MONO

    class disabled(ButtonDefault.disabled):
        text_style = ui.MONO


def render_button(
    text: Optional[str], icon: Optional[bytes], s: ButtonStyleStateType, area: ui.Area
) -> None:
    if in_area(area, 0, ui.HEIGHT - 1):
        is_right = False
    elif in_area(area, ui.WIDTH - 1, ui.HEIGHT - 1):
        is_right = True
    else:
        raise AssertionError

    ax, ay, aw, ah = area
    _render_background(text or "", s, is_right, area)
    _render_content(text or "", s, is_right, area)


def _bar_radius1(x: int, y: int, w: int, h: int, color: int) -> None:
    display.bar(x + 1, y, w - 2, h, color)
    display.bar(x, y + 1, 1, h - 2, color)
    display.bar(x + w - 1, y + 1, 1, h - 2, color)


def _render_background(
    text: str, s: ButtonStyleStateType, is_right: bool, area: ui.Area,
) -> None:
    text_width = display.text_width(text, s.text_style)
    _ax, ay, _aw, ah = area
    if s.radius > 0:
        _bar_radius1(
            ui.WIDTH - text_width - 3 if is_right else 0,  # x
            ay,  # y
            text_width + 3,  # w
            ah,  # h
            s.bg_color,  # fgcolor
        )
    else:
        display.bar(
            ui.WIDTH - text_width + 1 if is_right else 0,  # x
            ay,  # y
            text_width - 1,  # w
            ah,  # h
            s.bg_color,  # fgcolor
        )


def _render_content(
    text: str, s: ButtonStyleStateType, is_right: bool, _area: ui.Area,
) -> None:
    h_border = 2 if s.radius > 0 else 0
    if is_right:
        display.text_right(
            ui.WIDTH - h_border + 1,
            ui.HEIGHT - 2,
            text,
            s.text_style,
            s.fg_color,
            s.bg_color,
        )
    else:
        display.text(
            h_border, ui.HEIGHT - 2, text, s.text_style, s.fg_color, s.bg_color
        )
