from . import display, in_area, rotate_coords
from trezor import ui, loop


DEFAULT_BUTTON = {
    'bg-color': ui.BLACK,
    'fg-color': ui.WHITE,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
}
DEFAULT_BUTTON_ACTIVE = {
    'bg-color': ui.GREY,
    'fg-color': ui.BLACK,
    'text-style': ui.BOLD,
    'border-color': ui.GREY,
}

CANCEL_BUTTON = {
    'bg-color': ui.RED,
    'fg-color': ui.LIGHT_RED,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
}
CANCEL_BUTTON_ACTIVE = {
    'bg-color': ui.RED,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
}

CONFIRM_BUTTON = {
    'bg-color': ui.GREEN,
    'fg-color': ui.LIGHT_GREEN,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
}
CONFIRM_BUTTON_ACTIVE = {
    'bg-color': ui.GREEN,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
}

CLEAR_BUTTON = {
    'bg-color': ui.BLACK,
    'fg-color': ui.WHITE,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
}
CLEAR_BUTTON_ACTIVE = {
    'bg-color': ui.BLACK,
    'fg-color': ui.GREY,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
}

BTN_CLICKED = const(1)

BTN_STARTED = const(1)
BTN_ACTIVE = const(2)
BTN_DIRTY = const(4)


class Button():

    def __init__(self, area, content, normal_style=None, active_style=None, absolute=False):
        self.area = area
        self.content = content
        self.normal_style = normal_style or DEFAULT_BUTTON
        self.active_style = active_style or DEFAULT_BUTTON_ACTIVE
        self.absolute = absolute
        self.state = BTN_DIRTY

    def render(self):
        if not self.state & BTN_DIRTY:
            return
        state = self.state & ~BTN_DIRTY
        style = self.active_style if state & BTN_ACTIVE else self.normal_style
        ax, ay, aw, ah = self.area
        tx = ax + aw // 2
        ty = ay + ah // 2 + 8
        display.bar(ax, ay, aw, ah, style['border-color'])
        display.bar(ax + 1, ay + 1, aw - 2, ah - 2, style['bg-color'])

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

    def send(self, event, pos):
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

    def __iter__(self):
        while True:
            self.render()
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result
