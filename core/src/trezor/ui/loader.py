import utime
from micropython import const

from trezor import loop, res, ui

_TARGET_MS = const(1000)
_SHRINK_BY = const(2)


class Loader(ui.Widget):
    def __init__(self, style=ui.LDR_DEFAULT):
        self.target_ms = _TARGET_MS
        self.normal_style = style["normal"] or ui.LDR_DEFAULT["normal"]
        self.active_style = style["active"] or ui.LDR_DEFAULT["active"]
        self.start_ms = None
        self.stop_ms = None

    def start(self):
        self.start_ms = utime.ticks_ms()
        self.stop_ms = None

    def stop(self):
        if self.start_ms is not None and self.stop_ms is None:
            diff_ms = utime.ticks_ms() - self.start_ms
        else:
            diff_ms = 0
        self.stop_ms = utime.ticks_ms()
        return diff_ms >= self.target_ms

    def is_active(self):
        return self.start_ms is not None

    def render(self):
        target = self.target_ms
        start = self.start_ms
        stop = self.stop_ms
        now = utime.ticks_ms()
        if stop is None:
            r = min(now - start, target)
        else:
            r = max(stop - start + (stop - now) * _SHRINK_BY, 0)
            if r == 0:
                self.start_ms = None
                self.stop_ms = None
        if r == target:
            s = self.active_style
        else:
            s = self.normal_style
        if s["icon"] is None:
            ui.display.loader(r, -24, s["fg-color"], s["bg-color"])
        elif s["icon-fg-color"] is None:
            ui.display.loader(r, -24, s["fg-color"], s["bg-color"], res.load(s["icon"]))
        else:
            ui.display.loader(
                r,
                -24,
                s["fg-color"],
                s["bg-color"],
                res.load(s["icon"]),
                s["icon-fg-color"],
            )

    def __iter__(self):
        sleep = loop.sleep(1000000 // 30)  # 30 fps
        ui.display.bar(0, 32, ui.WIDTH, ui.HEIGHT - 83, ui.BG)  # clear
        while self.is_active():
            self.render()
            yield sleep
        ui.display.bar(0, 32, ui.WIDTH, ui.HEIGHT - 83, ui.BG)  # clear
