from . import utils
from . import display
from .utils import in_area
from trezor import loop


DEFAULT_BUTTON = {
    'bg-color': utils.BLACK,
    'fg-color': utils.WHITE,
    'text-style': utils.NORMAL,
    'border-color': utils.blend(utils.BLACK, utils.WHITE, 0.1),
}
DEFAULT_BUTTON_ACTIVE = {
    'bg-color': utils.GREY,
    'fg-color': utils.BLACK,
    'text-style': utils.BOLD,
    'border-color': utils.GREY,
}

CANCEL_BUTTON = {
    'bg-color': utils.blend(utils.BLACK, utils.RED, 0.3),
    'fg-color': utils.RED,
    'text-style': utils.NORMAL,
    'border-color': utils.blend(utils.BLACK, utils.RED, 0.6),
}
CANCEL_BUTTON_ACTIVE = {
    'bg-color': utils.RED,
    'fg-color': utils.WHITE,
    'text-style': utils.BOLD,
    'border-color': utils.RED,
}

CONFIRM_BUTTON = {
    'bg-color': utils.blend(utils.BLACK, utils.GREEN, 0.3),
    'fg-color': utils.GREEN,
    'text-style': utils.NORMAL,
    'border-color': utils.blend(utils.BLACK, utils.GREEN, 0.6),
}
CONFIRM_BUTTON_ACTIVE = {
    'bg-color': utils.GREEN,
    'fg-color': utils.WHITE,
    'text-style': utils.BOLD,
    'border-color': utils.GREEN,
}

BTN_CLICKED = const(1)

BTN_STARTED = const(1)
BTN_ACTIVE = const(2)
BTN_DIRTY = const(4)


class Button():



    def __init__(self, area, text, normal_style=None, active_style=None):
        self.area = area
        self.text = text
        self.normal_style = normal_style or DEFAULT_BUTTON
        self.active_style = active_style or DEFAULT_BUTTON_ACTIVE
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
        display.text_center(tx, ty, self.text,
                            style['text-style'],
                            style['fg-color'],
                            style['bg-color'])
        self.state = state

    def send(self, event, pos):
        if event is loop.TOUCH_START:
            if in_area(pos, self.area):
                self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
        elif event is loop.TOUCH_MOVE and self.state & BTN_STARTED:
            if in_area(pos, self.area):
                if not self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
            else:
                if self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY
        elif event is loop.TOUCH_END and self.state & BTN_STARTED:
            self.state = BTN_DIRTY
            if in_area(pos, self.area):
                return BTN_CLICKED
