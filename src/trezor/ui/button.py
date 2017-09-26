from micropython import const

from trezor import io
from trezor import ui

from trezor.ui import contains
from trezor.ui import display
from trezor.ui import rotate
from trezor.ui import Widget

BTN_CLICKED = const(1)

BTN_STARTED = const(1)
BTN_ACTIVE = const(2)
BTN_DIRTY = const(4)
BTN_DISABLED = const(8)


class Button(Widget):

    def __init__(self, area, content,
                 normal_style=None,
                 active_style=None,
                 disabled_style=None,
                 absolute=False):
        self.area = area
        self.content = content
        self.normal_style = normal_style or ui.BTN_DEFAULT
        self.active_style = active_style or ui.BTN_DEFAULT_ACTIVE
        self.disabled_style = disabled_style or ui.BTN_DEFAULT_DISABLED
        self.absolute = absolute
        self.state = BTN_DIRTY

    def enable(self):
        self.state &= ~BTN_DISABLED
        self.state |= BTN_DIRTY

    def disable(self):
        self.state |= BTN_DISABLED | BTN_DIRTY

    def taint(self):
        self.state |= BTN_DIRTY

    def render(self):
        if not self.state & BTN_DIRTY:
            return
        state = self.state & ~BTN_DIRTY
        if state & BTN_DISABLED:
            s = self.disabled_style
        elif state & BTN_ACTIVE:
            s = self.active_style
        else:
            s = self.normal_style
        ax, ay, aw, ah = self.area
        tx = ax + aw // 2
        ty = ay + ah // 2 + 8
        display.bar_radius(ax, ay, aw, ah,
                           s['border-color'],
                           ui.BG,
                           s['radius'])
        display.bar_radius(ax + 4, ay + 4, aw - 8, ah - 8,
                           s['bg-color'],
                           s['border-color'],
                           s['radius'])

        if isinstance(self.content, str):
            display.text_center(tx, ty, self.content,
                                s['text-style'],
                                s['fg-color'],
                                s['bg-color'])

        else:
            display.icon(tx - 15, ty - 20, self.content,
                         s['fg-color'],
                         s['bg-color'])

        self.state = state

    def touch(self, event, pos):
        if self.state & BTN_DISABLED:
            return
        if not self.absolute:
            pos = rotate(pos)
        if event == io.TOUCH_START:
            if contains(self.area, pos):
                self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
        elif event == io.TOUCH_MOVE and self.state & BTN_STARTED:
            if contains(self.area, pos):
                if not self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
            else:
                if self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY
        elif event == io.TOUCH_END and self.state & BTN_STARTED:
            self.state = BTN_DIRTY
            if contains(self.area, pos):
                return BTN_CLICKED
