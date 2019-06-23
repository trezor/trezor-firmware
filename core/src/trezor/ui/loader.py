import utime
from micropython import const

from trezor import res, ui
from trezor.ui import display


class LoaderDefault:
    class normal:
        bg_color = ui.BG
        fg_color = ui.GREEN
        icon = None
        icon_fg_color = None

    class active:
        bg_color = ui.BG
        fg_color = ui.GREEN
        icon = ui.ICON_CHECK
        icon_fg_color = ui.WHITE


class LoaderDanger:
    class normal(LoaderDefault.normal):
        fg_color = ui.RED

    class active(LoaderDefault.active):
        fg_color = ui.RED


_TARGET_MS = const(1000)


class Loader(ui.Control):
    def __init__(self, style=LoaderDefault):
        self.normal_style = style.normal
        self.active_style = style.active
        self.target_ms = _TARGET_MS
        self.start_ms = None
        self.stop_ms = None

    def start(self):
        self.start_ms = utime.ticks_ms()
        self.stop_ms = None
        self.on_start()

    def stop(self):
        self.stop_ms = utime.ticks_ms()

    def elapsed_ms(self):
        if self.start_ms is None:
            return 0
        return utime.ticks_ms() - self.start_ms

    def on_render(self):
        target = self.target_ms
        start = self.start_ms
        stop = self.stop_ms
        now = utime.ticks_ms()
        if stop is None:
            r = min(now - start, target)
        else:
            r = max(stop - start + (stop - now) * 2, 0)
        if r == target:
            s = self.active_style
        else:
            s = self.normal_style

        Y = const(-24)

        if s.icon is None:
            display.loader(r, False, Y, s.fg_color, s.bg_color)
        else:
            display.loader(
                r, False, Y, s.fg_color, s.bg_color, res.load(s.icon), s.icon_fg_color
            )
        if r == 0:
            self.start_ms = None
            self.stop_ms = None
            self.on_start()
        if r == target:
            self.on_finish()

    def on_start(self):
        pass

    def on_finish(self):
        pass


class LoadingAnimation(ui.Layout):
    def __init__(self, style=LoaderDefault):
        self.loader = Loader(style)
        self.loader.on_finish = self.on_finish
        self.loader.start()

    def dispatch(self, event, x, y):
        if not self.loader.elapsed_ms():
            self.loader.start()
        self.loader.dispatch(event, x, y)

    def on_finish(self):
        raise ui.Result(None)
