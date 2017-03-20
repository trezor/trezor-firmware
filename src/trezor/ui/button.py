from micropython import const
from trezor import ui, loop
from . import display, in_area, rotate_coords, Widget


DEFAULT_BUTTON = {
    'bg-color': ui.BLACKISH,
    'fg-color': ui.WHITE,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
    'radius': ui.BTN_RADIUS,
}
DEFAULT_BUTTON_ACTIVE = {
    'bg-color': ui.GREY,
    'fg-color': ui.BLACK,
    'text-style': ui.BOLD,
    'border-color': ui.GREY,
    'radius': ui.BTN_RADIUS,
}
DEFAULT_BUTTON_DISABLED = {
    'bg-color': ui.BLACK,
    'fg-color': ui.GREY,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
    'radius': ui.BTN_RADIUS,
}

CANCEL_BUTTON = {
    'bg-color': ui.RED,
    'fg-color': ui.LIGHT_RED,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
    'radius': ui.BTN_RADIUS,
}
CANCEL_BUTTON_ACTIVE = {
    'bg-color': ui.RED,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
    'radius': ui.BTN_RADIUS,
}

CONFIRM_BUTTON = {
    'bg-color': ui.GREEN,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
    'radius': ui.BTN_RADIUS,
}
CONFIRM_BUTTON_ACTIVE = {
    'bg-color': ui.GREEN,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
    'radius': ui.BTN_RADIUS,
}

CLEAR_BUTTON = {
    'bg-color': ui.BLACK,
    'fg-color': ui.WHITE,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
    'radius': ui.BTN_RADIUS,
}
CLEAR_BUTTON_ACTIVE = {
    'bg-color': ui.BLACK,
    'fg-color': ui.GREY,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
    'radius': ui.BTN_RADIUS,
}

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
        self.normal_style = normal_style or DEFAULT_BUTTON
        self.active_style = active_style or DEFAULT_BUTTON_ACTIVE
        self.disabled_style = disabled_style or DEFAULT_BUTTON_DISABLED
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
            style = self.disabled_style
        elif state & BTN_ACTIVE:
            style = self.active_style
        else:
            style = self.normal_style
        ax, ay, aw, ah = self.area
        tx = ax + aw // 2
        ty = ay + ah // 2 + 8
        display.bar_radius(ax, ay, aw, ah, style['border-color'], ui.BLACK, style['radius'])
        display.bar_radius(ax + 1, ay + 1, aw - 2, ah - 2, style['bg-color'], style['border-color'], style['radius'])

        if isinstance(self.content, str):
            display.text_center(tx, ty, self.content,
                                style['text-style'],
                                style['fg-color'],
                                style['bg-color'])

        else:
            display.icon(ax, ay, self.content,
                         style['fg-color'],
                         style['bg-color'])

        self.state = state

    def touch(self, event, pos):
        if self.state & BTN_DISABLED:
            return
        if not self.absolute:
            pos = rotate_coords(pos)
        if event == loop.TOUCH_START:
            if in_area(pos, self.area):
                self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
        elif event == loop.TOUCH_MOVE and self.state & BTN_STARTED:
            if in_area(pos, self.area):
                if not self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
            else:
                if self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY
        elif event == loop.TOUCH_END and self.state & BTN_STARTED:
            self.state = BTN_DIRTY
            if in_area(pos, self.area):
                return BTN_CLICKED
