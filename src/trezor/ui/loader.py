import utime
from micropython import const
from trezor import loop
from trezor import ui
from trezor import res


class Loader(ui.Widget):

    def __init__(self, target_ms=1000, normal_style=None, active_style=None):
        self.target_ms = target_ms
        self.start_ticks_ms = None
        self.normal_style = normal_style or ui.LDR_DEFAULT
        self.active_style = active_style or ui.LDR_DEFAULT_ACTIVE

    def start(self):
        self.start_ticks_ms = utime.ticks_ms()
        ui.display.bar(0, 32, 240, 240 - 80, ui.BG)

    def stop(self):
        ui.display.bar(0, 32, 240, 240 - 80, ui.BG)
        if self.start_ticks_ms is not None:
            ticks_diff = utime.ticks_ms() - self.start_ticks_ms
        else:
            ticks_diff = 0
        self.start_ticks_ms = None
        return ticks_diff >= self.target_ms

    def is_active(self):
        return self.start_ticks_ms is not None

    def render(self):
        progress = min(utime.ticks_ms() - self.start_ticks_ms, self.target_ms)
        if progress == self.target_ms:
            s = self.active_style
        else:
            s = self.normal_style
        if s['icon'] is None:
            ui.display.loader(
                progress, -8, s['fg-color'], s['bg-color'])
        elif s['icon-fg-color'] is None:
            ui.display.loader(
                progress, -8, s['fg-color'], s['bg-color'], res.load(s['icon']))
        else:
            ui.display.loader(
                progress, -8, s['fg-color'], s['bg-color'], res.load(s['icon']), s['icon-fg-color'])

    def __iter__(self):
        sleep = loop.sleep(1000000 // 60)  # 60 fps
        while self.is_active():
            self.render()
            yield sleep
