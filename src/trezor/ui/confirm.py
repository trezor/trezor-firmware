import utime
from .button import Button, BTN_CLICKED, BTN_STARTED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE
from trezor import loop, ui


CONFIRMED = const(1)
CANCELLED = const(2)


class ConfirmDialog():

    def __init__(self, content=None, confirm='Confirm', cancel='Cancel'):
        self.content = content
        self.confirm = Button((121, 240 - 48, 119, 48), confirm,
                              normal_style=CONFIRM_BUTTON,
                              active_style=CONFIRM_BUTTON_ACTIVE)
        self.cancel = Button((0, 240 - 48, 119, 48), cancel,
                             normal_style=CANCEL_BUTTON,
                             active_style=CANCEL_BUTTON_ACTIVE)

    def render(self):
        if self.content is not None:
            self.content.render()
        self.confirm.render()
        self.cancel.render()

    def send(self, event, pos):
        if self.confirm.send(event, pos) == BTN_CLICKED:
            return CONFIRMED
        if self.cancel.send(event, pos) == BTN_CLICKED:
            return CANCELLED
        if self.content is not None:
            return self.content.send(event, pos)

    def __iter__(self):
        while True:
            self.render()
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result


DEFAULT_LOADER = {
    'bg-color': ui.BLACK,
    'fg-color': ui.WHITE,
    'icon': None,
    'icon-fg-color': None,
}
DEFAULT_LOADER_ACTIVE = {
    'bg-color': ui.BLACK,
    'fg-color': ui.LIGHT_GREEN,
    'icon': None,
    'icon-fg-color': None,
}

LOADER_MSEC = const(1000)


class Loader():

    def __init__(self, normal_style=None, active_style=None):
        self.start_ticks_ms = None
        self.normal_style = normal_style or DEFAULT_LOADER
        self.active_style = active_style or DEFAULT_LOADER_ACTIVE

    def start(self):
        self.start_ticks_ms = utime.ticks_ms()

    def stop(self):
        ticks_diff = utime.ticks_ms() - self.start_ticks_ms
        self.start_ticks_ms = None
        return ticks_diff >= LOADER_MSEC

    def render(self):
        if self.start_ticks_ms is None:
            return False

        progress = min(utime.ticks_ms() - self.start_ticks_ms, LOADER_MSEC)
        if progress == LOADER_MSEC:
            style = self.active_style
        else:
            style = self.normal_style

        if style['icon'] is None:
            ui.display.loader(progress, style['fg-color'], style['bg-color'])
        elif style['icon-fg-color'] is None:
            ui.display.loader(
                progress, style['fg-color'], style['bg-color'], style['icon'])
        else:
            ui.display.loader(
                progress, style['fg-color'], style['bg-color'], style['icon'], style['icon-fg-color'])

        return True


class HoldToConfirmDialog():

    def __init__(self, button, content=None, *args, **kwargs):
        self.button = button
        self.content = content
        self.loader = Loader(*args, **kwargs)

    def render(self):
        if not self.loader.render():
            if self.content is not None:
                self.content.render()
            else:
                ui.display.bar(0, 0, 240, 240 - 48, ui.BLACK)
        self.button.render()

    def send(self, event, pos):
        if self.content is not None:
            self.content.send(pos)
        button = self.button
        was_started = button.state & BTN_STARTED
        button.send(event, pos)
        is_started = button.state & BTN_STARTED
        if is_started:
            if not was_started:
                self.loader.start()
        else:
            if was_started:
                if self.loader.stop():
                    return CONFIRMED
        return None

    async def __iter__(self):
        await loop.Wait([self._render_loop(),
                         self._event_loop()])

    def _render_loop(self):
        RENDER_DELAY = const(1000000 // 60)
        while True:
            self.render()
            yield loop.Sleep(RENDER_DELAY)

    def _event_loop(self):
        while True:
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result
