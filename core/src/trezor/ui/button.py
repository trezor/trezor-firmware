from micropython import const

from trezor import ui
from trezor.ui import display, in_area


class ButtonDefault:
    class normal:
        bg_color = ui.BLACKISH
        fg_color = ui.FG
        text_style = ui.BOLD
        border_color = ui.BG
        radius = ui.RADIUS

    class active:
        bg_color = ui.FG
        fg_color = ui.BLACKISH
        text_style = ui.BOLD
        border_color = ui.FG
        radius = ui.RADIUS

    class disabled:
        bg_color = ui.BG
        fg_color = ui.GREY
        text_style = ui.NORMAL
        border_color = ui.BG
        radius = ui.RADIUS


class ButtonMono(ButtonDefault):
    class normal(ButtonDefault.normal):
        text_style = ui.MONO

    class active(ButtonDefault.active):
        text_style = ui.MONO

    class disabled(ButtonDefault.disabled):
        text_style = ui.MONO


class ButtonMonoDark:
    class normal:
        bg_color = ui.DARK_BLACK
        fg_color = ui.DARK_WHITE
        text_style = ui.MONO
        border_color = ui.BG
        radius = ui.RADIUS

    class active:
        bg_color = ui.FG
        fg_color = ui.DARK_BLACK
        text_style = ui.MONO
        border_color = ui.FG
        radius = ui.RADIUS

    class disabled:
        bg_color = ui.DARK_BLACK
        fg_color = ui.GREY
        text_style = ui.MONO
        border_color = ui.BG
        radius = ui.RADIUS


class ButtonConfirm(ButtonDefault):
    class normal(ButtonDefault.normal):
        bg_color = ui.GREEN

    class active(ButtonDefault.active):
        fg_color = ui.GREEN


class ButtonCancel(ButtonDefault):
    class normal(ButtonDefault.normal):
        bg_color = ui.RED

    class active(ButtonDefault.active):
        fg_color = ui.RED


class ButtonClear(ButtonDefault):
    class normal(ButtonDefault.normal):
        bg_color = ui.ORANGE

    class active(ButtonDefault.active):
        fg_color = ui.ORANGE


class ButtonMonoConfirm(ButtonDefault):
    class normal(ButtonDefault.normal):
        text_style = ui.MONO
        bg_color = ui.GREEN

    class active(ButtonDefault.active):
        text_style = ui.MONO
        fg_color = ui.GREEN

    class disabled(ButtonDefault.disabled):
        text_style = ui.MONO


# button states
_INITIAL = const(0)
_PRESSED = const(1)
_RELEASED = const(2)
_DISABLED = const(3)

# button constants
_ICON = const(16)  # icon size in pixels
_BORDER = const(4)  # border size in pixels


class Button(ui.Control):
    def __init__(self, area, content, style=ButtonDefault):
        self.area = area
        self.content = content
        self.normal_style = style.normal
        self.active_style = style.active
        self.disabled_style = style.disabled
        self.state = _INITIAL
        self.repaint = True

    def enable(self):
        if self.state is not _INITIAL:
            self.state = _INITIAL
            self.repaint = True

    def disable(self):
        if self.state is not _DISABLED:
            self.state = _DISABLED
            self.repaint = True

    def on_render(self):
        if self.repaint:
            if self.state is _DISABLED:
                s = self.disabled_style
            elif self.state is _PRESSED:
                s = self.active_style
            else:
                s = self.normal_style
            ax, ay, aw, ah = self.area
            self.render_background(s, ax, ay, aw, ah)
            self.render_content(s, ax, ay, aw, ah)
            self.repaint = False

    def render_background(self, s, ax, ay, aw, ah):
        radius = s.radius
        bg_color = s.bg_color
        border_color = s.border_color
        if border_color == bg_color:
            # we don't need to render the border
            display.bar_radius(ax, ay, aw, ah, bg_color, ui.BG, radius)
        else:
            # render border and background on top of it
            display.bar_radius(ax, ay, aw, ah, border_color, ui.BG, radius)
            display.bar_radius(
                ax + _BORDER,
                ay + _BORDER,
                aw - _BORDER * 2,
                ah - _BORDER * 2,
                bg_color,
                border_color,
                radius,
            )

    def render_content(self, s, ax, ay, aw, ah):
        tx = ax + aw // 2
        ty = ay + ah // 2 + 8
        t = self.content
        if isinstance(t, str):
            display.text_center(tx, ty, t, s.text_style, s.fg_color, s.bg_color)
        elif isinstance(t, bytes):
            display.icon(tx - _ICON // 2, ty - _ICON, t, s.fg_color, s.bg_color)

    def on_touch_start(self, x, y):
        if self.state is _DISABLED:
            return
        if in_area(self.area, x, y):
            self.state = _PRESSED
            self.repaint = True
            self.on_press_start()

    def on_touch_move(self, x, y):
        if self.state is _DISABLED:
            return
        if in_area(self.area, x, y):
            if self.state is _RELEASED:
                self.state = _PRESSED
                self.repaint = True
                self.on_press_start()
        else:
            if self.state is _PRESSED:
                self.state = _RELEASED
                self.repaint = True
                self.on_press_end()

    def on_touch_end(self, x, y):
        state = self.state
        if state is not _INITIAL and state is not _DISABLED:
            self.state = _INITIAL
            self.repaint = True
        if in_area(self.area, x, y):
            if state is _PRESSED:
                self.on_press_end()
                self.on_click()

    def on_press_start(self):
        pass

    def on_press_end(self):
        pass

    def on_click(self):
        pass
