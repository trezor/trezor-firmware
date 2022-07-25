import utime
from micropython import const
from typing import Any, Tuple

import storage
import storage.cache
import storage.device
from trezor import config, io, loop, ui, utils
from trezor.ui.loader import Loader, LoaderNeutral

from apps.base import lock_device

from . import HomescreenBase

_LOADER_DELAY_MS = const(500)
_LOADER_TOTAL_MS = const(2500)


# Overall TODO for the modelR vs modelT:
# - we could somehow make sure that code unused by the other
# model is not included in the binary
# (R does not need any code regarding touch-screen etc.)


async def homescreen() -> None:
    """Is model-specific."""
    if utils.MODEL in ("T",):
        await HomescreenModelT()
    elif utils.MODEL in ("R",):
        await HomescreenModelR()
    elif utils.MODEL in ("1",):
        await HomescreenModel1()
    lock_device()


def render_top_header() -> None:
    """Common for all the models."""
    if storage.device.is_initialized() and storage.device.no_backup():
        ui.header_error("SEEDLESS")
    elif storage.device.is_initialized() and storage.device.unfinished_backup():
        ui.header_error("BACKUP FAILED!")
    elif storage.device.is_initialized() and storage.device.needs_backup():
        ui.header_warning("NEEDS BACKUP!")
    elif storage.device.is_initialized() and not config.has_pin():
        ui.header_warning("PIN NOT SET!")
    elif storage.device.get_experimental_features():
        # TODO: this is so long for model R that it collides with icons
        # Could remove icons in this case, or change it to
        # "EXPRMNTL MODE" or just "EXPERIMENTAL"
        ui.header_warning("EXPERIMENTAL MODE!")
    else:
        ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)

    if not utils.usb_data_connected():
        ui.header_error("NO USB CONNECTION")


class render_header_and_refresh:
    """Context manager to render the top header and refresh the screen afterwards."""

    def __init__(self) -> None:
        pass

    def __enter__(self) -> None:
        render_top_header()

    def __exit__(self, *args: Any) -> None:
        ui.refresh()


class HomescreenModelR(HomescreenBase):
    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()

    def do_render(self) -> None:
        with render_header_and_refresh():
            # When not initialized, showing the instruction text on two lines,
            # as it cannot all fit on one line. In that case also putting
            # the icon more on the top.
            # Otherwise just showing the uppercase label in monospace.
            if not storage.device.is_initialized():
                ui.display.icon(34, 18, self.get_avatar(), ui.style.FG, ui.style.BG)
                ui.display.text_center(
                    ui.WIDTH // 2, 98, "Go to", ui.BOLD, ui.FG, ui.BG
                )
                ui.display.text_center(
                    ui.WIDTH // 2, 112, "trezor.io/start", ui.BOLD, ui.FG, ui.BG
                )
            else:
                ui.display.icon(34, 28, self.get_avatar(), ui.style.FG, ui.style.BG)
                ui.display.text_center(
                    ui.WIDTH // 2, 112, self.label.upper(), ui.MONO, ui.FG, ui.BG
                )


class HomescreenModel1(HomescreenBase):
    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()
        if not storage.device.is_initialized():
            self.label = "Go to trezor.io/start"

    def do_render(self) -> None:
        with render_header_and_refresh():
            ui.display.icon(33, 14, self.get_avatar(), ui.style.FG, ui.style.BG)
            ui.display.text_center(ui.WIDTH // 2, 60, self.label, ui.BOLD, ui.FG, ui.BG)


class HomescreenModelT(HomescreenBase):
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

    def create_tasks(self) -> Tuple[loop.AwaitableTask, ...]:
        return super().create_tasks() + (self.usb_checker_task(),)

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
