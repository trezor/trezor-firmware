import utime
from micropython import const
from typing import Any, Tuple

import storage.cache
import storage.device
from trezor import io, loop, res, ui, utils
from trezor.ui.loader import Loader, LoaderNeutral

from apps.base import set_homescreen

from . import draw_simple_text


class HomescreenBase(ui.Layout):
    RENDER_INDICATOR: object | None = None

    def __init__(self, label: str | None) -> None:
        super().__init__()
        self.label = label or "My Trezor"
        self.repaint = storage.cache.homescreen_shown is not self.RENDER_INDICATOR

    def get_image(self) -> bytes:
        return storage.device.get_homescreen() or res.load(
            "apps/homescreen/res/bg.toif"
        )

    async def __iter__(self) -> Any:
        # We need to catch the ui.Cancelled exception that kills us, because that means
        # that we will need to draw on screen again after restart.
        try:
            return await super().__iter__()
        except ui.Cancelled:
            storage.cache.homescreen_shown = None
            raise

    def on_render(self) -> None:
        if not self.repaint:
            return
        self.do_render()
        self.set_repaint(False)

    def do_render(self) -> None:
        raise NotImplementedError

    def set_repaint(self, value: bool) -> None:
        self.repaint = value
        storage.cache.homescreen_shown = None if value else self.RENDER_INDICATOR

    def _before_render(self) -> None:
        if storage.cache.homescreen_shown is not self.RENDER_INDICATOR:
            super()._before_render()


_LOADER_DELAY_MS = const(500)
_LOADER_TOTAL_MS = const(2500)


class Homescreen(HomescreenBase):
    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(
        self,
        label: str | None,
        notification: str | None,
        notification_is_error: bool,
        hold_to_lock: bool,
    ) -> None:
        super().__init__(label=label)
        self.notification = notification
        self.notification_is_error = notification_is_error
        self.hold_to_lock = hold_to_lock

        self.loader = Loader(
            style=LoaderNeutral,
            target_ms=_LOADER_TOTAL_MS - _LOADER_DELAY_MS,
            offset_y=-10,
            reverse_speedup=3,
        )
        self.touch_ms: int | None = None

    def create_tasks(self) -> Tuple[loop.AwaitableTask, ...]:
        return super().create_tasks() + (self.usb_checker_task(),)

    async def usb_checker_task(self) -> None:
        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            await usbcheck
            self.set_repaint(True)

    def do_render(self) -> None:
        # warning bar on top
        if not utils.usb_data_connected():
            ui.header_error("NO USB CONNECTION")
        elif self.notification is not None:
            if self.notification_is_error:
                ui.header_error(self.notification)
            else:
                ui.header_warning(self.notification)
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.get_header_height(), ui.BG)

        # homescreen with shifted avatar and text on bottom
        # Differs for each model
        # TODO: support homescreen avatar change for R and 1
        if utils.MODEL in ("T",):
            ui.display.avatar(48, 48 - 10, self.get_image(), ui.WHITE, ui.BLACK)
        elif utils.MODEL in ("R",):
            icon = "trezor/res/homescreen_model_r.toif"  # 92x92 px
            ui.display.icon(18, 18, ui.res.load(icon), ui.style.FG, ui.style.BG)
        elif utils.MODEL in ("1",):
            icon = "trezor/res/homescreen_model_1.toif"  # 64x36 px
            ui.display.icon(33, 14, ui.res.load(icon), ui.style.FG, ui.style.BG)

        label_heights = {"1": 60, "R": 120, "T": 220}
        ui.display.text_center(
            ui.WIDTH // 2, label_heights[utils.MODEL], self.label, ui.BOLD, ui.FG, ui.BG
        )

        ui.refresh()

    def on_touch_start(self, _x: int, _y: int) -> None:
        if self.loader.start_ms is not None:
            self.loader.start()
        elif self.hold_to_lock:
            self.touch_ms = utime.ticks_ms()

    def on_touch_end(self, _x: int, _y: int) -> None:
        if self.loader.start_ms is not None:
            ui.display.clear()
            self.set_repaint(True)
        self.loader.stop()
        self.touch_ms = None

        # raise here instead of self.loader.on_finish so as not to send TOUCH_END to the lockscreen
        if self.loader.elapsed_ms() >= self.loader.target_ms:
            raise ui.Result(None)

    def _loader_start(self) -> None:
        ui.display.clear()
        ui.display.text_center(ui.WIDTH // 2, 35, "Hold to lock", ui.BOLD, ui.FG, ui.BG)
        self.loader.start()

    def dispatch(self, event: int, x: int, y: int) -> None:
        if (
            self.touch_ms is not None
            and self.touch_ms + _LOADER_DELAY_MS < utime.ticks_ms()
        ):
            self.touch_ms = None
            self._loader_start()

        if event is ui.RENDER and self.loader.start_ms is not None:
            self.loader.dispatch(event, x, y)
        else:
            super().dispatch(event, x, y)


class Lockscreen(HomescreenBase):
    BACKLIGHT_LEVEL = ui.BACKLIGHT_LOW
    RENDER_SLEEP = loop.SLEEP_FOREVER
    RENDER_INDICATOR = storage.cache.LOCKSCREEN_ON

    def __init__(self, label: str | None, bootscreen: bool = False) -> None:
        if bootscreen:
            self.BACKLIGHT_LEVEL = ui.BACKLIGHT_NORMAL
            self.lock_label = "Not connected"
            self.tap_label = "Tap to connect"
        else:
            self.lock_label = "Locked"
            self.tap_label = "Tap to unlock"

        super().__init__(label=label)

    def do_render(self) -> None:
        # homescreen with label text on top
        ui.display.text_center(
            ui.WIDTH // 2, 35, self.label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )
        ui.display.avatar(48, 48, self.get_image(), ui.WHITE, ui.BLACK)

        # lock bar
        ui.display.bar_radius(40, 100, 160, 40, ui.TITLE_GREY, ui.BG, 4)
        ui.display.bar_radius(42, 102, 156, 36, ui.BG, ui.TITLE_GREY, 4)
        ui.display.text_center(
            ui.WIDTH // 2, 128, self.lock_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )

        # "tap to unlock"
        ui.display.text_center(
            ui.WIDTH // 2 + 10, 220, self.tap_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )
        ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.TITLE_GREY, ui.BG)

    def on_touch_end(self, _x: int, _y: int) -> None:
        raise ui.Result(None)


class Busyscreen(HomescreenBase):
    RENDER_INDICATOR = storage.cache.BUSYSCREEN_ON

    def __init__(self, delay_ms: int):
        super().__init__(label=None)
        self.delay_ms = delay_ms

    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        return self.handle_rendering(), self.handle_input(), self.handle_expiry()

    def handle_expiry(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        yield loop.sleep(self.delay_ms)
        storage.cache.delete(storage.cache.APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        raise ui.Result(None)

    def do_render(self) -> None:
        draw_simple_text(
            "Please wait", "CoinJoin in progress.\n\nDo not disconnect your\nTrezor."
        )
