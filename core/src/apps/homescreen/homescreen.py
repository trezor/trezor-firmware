import utime
from micropython import const

import storage
import storage.cache
import storage.device
from trezor import config, ui
from trezor.ui.loader import Loader, LoaderNeutral

from apps.base import lock_device

from . import HomescreenBase

_LOADER_DELAY_MS = const(500)
_LOADER_TOTAL_MS = const(2500)


async def homescreen() -> None:
    await Homescreen()
    lock_device()


class Homescreen(HomescreenBase):
    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()
        if not storage.device.is_initialized():
            self.label = "Go to trezor.io/start"

        self.loader = Loader(
            style=LoaderNeutral,
            target_ms=_LOADER_TOTAL_MS - _LOADER_DELAY_MS,
            offset_y=-10,
            reverse_speedup=3,
        )
        self.touch_ms: int | None = None

    def do_render(self) -> None:
        # warning bar on top
        if storage.device.is_initialized() and storage.device.no_backup():
            ui.header_error("SEEDLESS")
        elif storage.device.is_initialized() and storage.device.unfinished_backup():
            ui.header_error("BACKUP FAILED!")
        elif storage.device.is_initialized() and storage.device.needs_backup():
            ui.header_warning("NEEDS BACKUP!")
        elif storage.device.is_initialized() and not config.has_pin():
            ui.header_warning("PIN NOT SET!")
        elif storage.device.get_experimental_features():
            ui.header_warning("EXPERIMENTAL MODE!")
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)

        # homescreen with shifted avatar and text on bottom
        ui.display.avatar(48, 48 - 10, self.get_image(), ui.WHITE, ui.BLACK)
        ui.display.text_center(ui.WIDTH // 2, 220, self.label, ui.BOLD, ui.FG, ui.BG)

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
