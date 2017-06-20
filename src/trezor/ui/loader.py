import utime
from micropython import const
from trezor import loop
from trezor import ui


DEFAULT_LOADER = {
    'bg-color': ui.BLACK,
    'fg-color': ui.WHITE,
    'icon': None,
    'icon-fg-color': None,
}
DEFAULT_LOADER_ACTIVE = {
    'bg-color': ui.BLACK,
    'fg-color': ui.ACTIVE_GREEN,
    'icon': None,
    'icon-fg-color': None,
}

_LOADER_MSEC = const(1000)


class Loader(ui.Widget):

    def __init__(self, normal_style=None, active_style=None):
        self.start_ticks_ms = None
        self.normal_style = normal_style or DEFAULT_LOADER
        self.active_style = active_style or DEFAULT_LOADER_ACTIVE

    def start(self):
        self.start_ticks_ms = utime.ticks_ms()
        ui.display.bar(0, 32, 240, 240 - 80, ui.BLACK)

    def stop(self):
        ui.display.bar(0, 32, 240, 240 - 80, ui.BLACK)
        ticks_diff = utime.ticks_ms() - self.start_ticks_ms
        self.start_ticks_ms = None
        return ticks_diff >= _LOADER_MSEC

    def is_active(self):
        return self.start_ticks_ms is not None

    def render(self):
        progress = min(utime.ticks_ms() - self.start_ticks_ms, _LOADER_MSEC)
        if progress == _LOADER_MSEC:
            style = self.active_style
        else:
            style = self.normal_style
        if style['icon'] is None:
            ui.display.loader(
                progress, -8, style['fg-color'], style['bg-color'])
        elif style['icon-fg-color'] is None:
            ui.display.loader(
                progress, -8, style['fg-color'], style['bg-color'], style['icon'])
        else:
            ui.display.loader(
                progress, -8, style['fg-color'], style['bg-color'], style['icon'], style['icon-fg-color'])

    def __iter__(self):
        sleep = loop.sleep(1000000 // 60)  # 60 fps
        while self.is_active():
            self.render()
            yield sleep
