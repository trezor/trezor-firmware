import utime
from micropython import const
from typing import Tuple

import storage
import storage.cache
import storage.device
from trezor import config, io, loop, ui, utils
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

    def create_tasks(self) -> Tuple[loop.AwaitableTask, ...]:
        return super().create_tasks() + (self.usb_checker_task(),)

    async def usb_checker_task(self) -> None:
        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            await usbcheck
            self.set_repaint(True)

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
            ui.display.bar(0, 0, ui.WIDTH, ui.get_header_height(), ui.BG)

        # homescreen with shifted avatar and text on bottom
        # Differs for each model

        if not utils.usb_data_connected():
            ui.header_error("NO USB CONNECTION")

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
        elif config.has_pin():
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
