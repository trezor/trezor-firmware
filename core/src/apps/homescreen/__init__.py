from typing import Any, Tuple

import storage.cache
import storage.device
from trezor import config, io, loop, res, ui, utils


def render_top_header() -> None:
    """Common for all the models. Draws the top header."""
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


class HomescreenBase(ui.Layout):
    """Common base class for all model-specific homescreens."""

    RENDER_INDICATOR: object | None = None

    def __init__(self) -> None:
        super().__init__()
        self.label = storage.device.get_label() or "My Trezor"
        self.repaint = storage.cache.homescreen_shown is not self.RENDER_INDICATOR
        self.is_connected = False

    def create_tasks(self) -> Tuple[loop.AwaitableTask, ...]:
        return super().create_tasks() + (self.usb_checker_task(),)

    async def usb_checker_task(self) -> None:
        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            is_connected = await usbcheck
            if is_connected != self.is_connected:
                self.is_connected = is_connected
                self.set_repaint(True)

    def get_avatar(self) -> bytes:
        """Returns the image for homescreen. Is model-specific."""
        if utils.MODEL in ("T",):
            return storage.device.get_homescreen() or res.load(
                "apps/homescreen/res/bg.toif"
            )
        elif utils.MODEL in ("1", "R"):
            # TODO: make it possible to change
            # TODO: make it a requirement of XxX px
            # TODO: support it for ui.display.avatar, not only ui.display.icon
            return res.load("trezor/res/homescreen_model_1.toif")  # 64x36 px
        else:
            raise Exception("Unknown model")

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
        """To be overridden by subclasses."""
        raise NotImplementedError

    def set_repaint(self, value: bool) -> None:
        self.repaint = value
        storage.cache.homescreen_shown = None if value else self.RENDER_INDICATOR

    def _before_render(self) -> None:
        if storage.cache.homescreen_shown is not self.RENDER_INDICATOR:
            super()._before_render()
