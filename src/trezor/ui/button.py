from micropython import const

from trezor import io
from trezor import ui

from trezor.ui import contains
from trezor.ui import display
from trezor.ui import rotate
from trezor.ui import LazyWidget

# button events
BTN_CLICKED = const(1)

# button states
BTN_INITIAL = const(0)
BTN_DISABLED = const(1)
BTN_FOCUSED = const(2)
BTN_ACTIVE = const(3)

# constants
ICON = const(16)  # icon size in pixels
BORDER = const(4)  # border size in pixels


class Button(LazyWidget):

    def __init__(self, area: tuple, content: str, style: dict = ui.BTN_KEY):
        self.area = area
        self.content = content
        self.normal_style = style['normal'] or ui.BTN_KEY['normal']
        self.active_style = style['active'] or ui.BTN_KEY['active']
        self.disabled_style = style['disabled'] or ui.BTN_KEY['disabled']
        self.state = BTN_INITIAL

    def enable(self):
        if self.state == BTN_DISABLED:
            self.state = BTN_INITIAL
            self.render_next_frame = True

    def disable(self):
        if self.state != BTN_DISABLED:
            self.state = BTN_DISABLED
            self.render_next_frame = True

    def render(self):
        state = self.state
        if state == BTN_DISABLED:
            s = self.disabled_style
        elif state == BTN_ACTIVE:
            s = self.active_style
        else:
            s = self.normal_style
        ax, ay, aw, ah = self.area
        self.render_background(s, ax, ay, aw, ah)
        self.render_content(s, ax, ay, aw, ah)

    def render_background(self, s, ax, ay, aw, ah):
        radius = s['radius']
        bg_color = s['bg-color']
        border_color = s['border-color']
        if border_color != bg_color:
            # render border and background on top of it
            display.bar_radius(ax, ay,
                               aw, ah,
                               border_color,
                               ui.BG,
                               radius)
            display.bar_radius(ax + BORDER, ay + BORDER,
                               aw - BORDER * 2, ah - BORDER * 2,
                               bg_color,
                               border_color,
                               radius)
        else:
            # render only the background
            display.bar_radius(ax, ay,
                               aw, ah,
                               bg_color,
                               ui.BG,
                               radius)

    def render_content(self, s, ax, ay, aw, ah):
        c = self.content
        tx = ax + aw // 2
        ty = ay + ah // 2 + 8
        if isinstance(c, str):
            display.text_center(
                tx, ty, c, s['text-style'], s['fg-color'], s['bg-color'])
        else:
            display.icon(
                tx - ICON // 2, ty - ICON, c, s['fg-color'], s['bg-color'])

    def touch(self, event, pos):
        pos = rotate(pos)

        state = self.state
        if state == BTN_DISABLED:
            return

        if event == io.TOUCH_START:
            if contains(self.area, pos):
                self.state = BTN_ACTIVE
                self.render_next_frame = True

        elif event == io.TOUCH_MOVE:
            if contains(self.area, pos):
                if state == BTN_FOCUSED:
                    self.state = BTN_ACTIVE
                    self.render_next_frame = True
            else:
                if state == BTN_ACTIVE:
                    self.state = BTN_FOCUSED
                    self.render_next_frame = True

        elif event == io.TOUCH_END:
            self.state = BTN_INITIAL
            self.render_next_frame = True
            if state == BTN_ACTIVE and contains(self.area, pos):
                return BTN_CLICKED
