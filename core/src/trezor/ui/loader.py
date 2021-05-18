import utime
from micropython import const

from trezor import res, ui, utils
from trezor.ui import display


class LoaderDefault:
    class normal:
        bg_color = ui.BG
        fg_color = ui.GREEN
        icon: str | None = None
        icon_fg_color: int | None = None

    class active(normal):
        bg_color = ui.BG
        fg_color = ui.GREEN
        icon: str | None = ui.ICON_CHECK
        icon_fg_color: int | None = ui.WHITE


class LoaderDanger(LoaderDefault):
    class normal(LoaderDefault.normal):
        fg_color = ui.RED

    class active(LoaderDefault.active):
        fg_color = ui.RED


class LoaderNeutral(LoaderDefault):
    class normal(LoaderDefault.normal):
        fg_color = ui.FG

    class active(LoaderDefault.active):
        fg_color = ui.FG


if False:
    LoaderStyleType = type[LoaderDefault]


_TARGET_MS = const(1000)
_OFFSET_Y = const(-24)
_REVERSE_SPEEDUP = const(2)


class Loader(ui.Component):
    def __init__(
        self,
        style: LoaderStyleType = LoaderDefault,
        target_ms: int = _TARGET_MS,
        offset_y: int = _OFFSET_Y,
        reverse_speedup: int = _REVERSE_SPEEDUP,
    ) -> None:
        super().__init__()
        self.normal_style = style.normal
        self.active_style = style.active
        self.target_ms = target_ms
        self.start_ms: int | None = None
        self.stop_ms: int | None = None
        self.offset_y = offset_y
        self.reverse_speedup = reverse_speedup

    def start(self) -> None:
        if self.start_ms is not None and self.stop_ms is not None:
            self.start_ms = utime.ticks_ms() - self.elapsed_ms()
        else:
            self.start_ms = utime.ticks_ms()
        self.stop_ms = None
        self.on_start()

    def stop(self) -> None:
        self.stop_ms = utime.ticks_ms()

    def elapsed_ms(self) -> int:
        start = self.start_ms
        stop = self.stop_ms
        now = utime.ticks_ms()
        if start is None:
            return 0
        elif stop is not None:
            return max(stop - start + (stop - now) * self.reverse_speedup, 0)
        else:
            return min(now - start, self.target_ms)

    def on_render(self) -> None:
        if self.start_ms is None:
            return
        target = self.target_ms
        r = self.elapsed_ms()
        if r != target:
            s = self.normal_style
        else:
            s = self.active_style

        progress = r * 1000 // target  # scale to 0-1000
        if s.icon is None:
            display.loader(progress, False, self.offset_y, s.fg_color, s.bg_color)
        else:
            display.loader(
                progress,
                False,
                self.offset_y,
                s.fg_color,
                s.bg_color,
                res.load(s.icon),
                s.icon_fg_color,
            )
        if (r == 0) and (self.stop_ms is not None):
            self.start_ms = None
            self.stop_ms = None
            self.on_start()
        if r == target:
            self.on_finish()

    def on_start(self) -> None:
        pass

    def on_finish(self) -> None:
        pass


class LoadingAnimation(ui.Layout):
    def __init__(self, style: LoaderStyleType = LoaderDefault) -> None:
        super().__init__()
        self.loader = Loader(style)
        self.loader.on_finish = self.on_finish  # type: ignore
        self.loader.start()

    def dispatch(self, event: int, x: int, y: int) -> None:
        if not self.loader.elapsed_ms():
            self.loader.start()
        self.loader.dispatch(event, x, y)

        if utils.DISABLE_ANIMATION:
            self.on_finish()

    def on_finish(self) -> None:
        raise ui.Result(None)
