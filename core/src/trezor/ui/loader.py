import utime
from micropython import const

from trezor import res, ui, utils
from trezor.ui import display

if False:
    from typing import Optional, Type


class LoaderDefault:
    class normal:
        bg_color = ui.BG
        fg_color = ui.GREEN
        icon: Optional[str] = None
        icon_fg_color: Optional[int] = None

    class active(normal):
        bg_color = ui.BG
        fg_color = ui.GREEN
        icon: Optional[str] = ui.ICON_CHECK
        icon_fg_color: Optional[int] = ui.WHITE


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
    LoaderStyleType = Type[LoaderDefault]


_TARGET_MS = const(1000)
_OFFSET_Y = const(-24)


class Loader(ui.Component):
    def __init__(
        self,
        style: LoaderStyleType = LoaderDefault,
        target_ms: int = _TARGET_MS,
        offset_y: int = _OFFSET_Y,
    ) -> None:
        super().__init__()
        self.normal_style = style.normal
        self.active_style = style.active
        self.target_ms = target_ms
        self.start_ms: Optional[int] = None
        self.stop_ms: Optional[int] = None
        self.offset_y = offset_y

    def start(self) -> None:
        self.start_ms = utime.ticks_ms()
        self.stop_ms = None
        self.on_start()

    def stop(self) -> None:
        self.stop_ms = utime.ticks_ms()

    def elapsed_ms(self) -> int:
        if self.start_ms is None:
            return 0
        return utime.ticks_ms() - self.start_ms

    def on_render(self) -> None:
        target = self.target_ms
        start = self.start_ms
        stop = self.stop_ms
        if start is None:
            return
        now = utime.ticks_ms()
        if stop is None:
            r = min(now - start, target)
        else:
            r = max(stop - start + (stop - now) * 2, 0)
        if r != target:
            s = self.normal_style
        else:
            s = self.active_style

        progress = r * 1000 // target
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
