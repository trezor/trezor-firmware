import utime
from micropython import const

import storage
import storage.cache
import storage.device
from trezor import config, io, loop, res, ui
from trezor.ui.loader import Loader, LoaderNeutral

from . import HomescreenBase, render_header_and_refresh

_LOADER_DELAY_MS = const(500)
_LOADER_TOTAL_MS = const(2500)


class Homescreen(HomescreenBase):
    """Homescreen for model T."""

    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()
        self.is_connected = False
        if not storage.device.is_initialized():
            self.label = "Go to trezor.io/start"

        self.loader = Loader(
            style=LoaderNeutral,
            target_ms=_LOADER_TOTAL_MS - _LOADER_DELAY_MS,
            offset_y=-10,
            reverse_speedup=3,
        )
        self.touch_ms: int | None = None

    # TODO: doing this for model R results in infinite loop of emulator logs with
    # "AttributeError: 'module' object has no attribute 'USB_CHECK'"
    async def usb_checker_task(self) -> None:
        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            is_connected = await usbcheck
            if is_connected != self.is_connected:
                self.is_connected = is_connected
                self.set_repaint(True)

    def do_render(self) -> None:
        with render_header_and_refresh():
            ui.display.avatar(48, 48 - 10, self.get_avatar(), ui.WHITE, ui.BLACK)
            ui.display.text_center(
                ui.WIDTH // 2, 220, self.label, ui.BOLD, ui.FG, ui.BG
            )

    def on_touch_start(self, _x: int, _y: int) -> None:
        if self.loader.start_ms is not None:
            self.loader.start()
        elif config.has_pin():
            self.touch_ms = utime.ticks_ms()

    def on_touch_end(self, _x: int, _y: int) -> None:
        if self.loader.start_ms is not None:
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
    """Lockscreen for model T."""

    BACKLIGHT_LEVEL = ui.BACKLIGHT_LOW
    RENDER_SLEEP = loop.SLEEP_FOREVER
    RENDER_INDICATOR = storage.cache.LOCKSCREEN_ON

    def __init__(self, bootscreen: bool = False) -> None:
        if bootscreen:
            self.BACKLIGHT_LEVEL = ui.BACKLIGHT_NORMAL
            self.lock_label = "Not connected"
            self.tap_label = "Tap to connect"
        else:
            self.lock_label = "Locked"
            self.tap_label = "Tap to unlock"

        super().__init__()

    def do_render(self) -> None:
        # homescreen with label text on top
        ui.display.text_center(
            ui.WIDTH // 2, 35, self.label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )
        ui.display.avatar(48, 48, self.get_avatar(), ui.WHITE, ui.BLACK)

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
        """Going to the PIN screen after tapping the display."""
        raise ui.Result(None)
