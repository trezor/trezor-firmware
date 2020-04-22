import storage
import storage.device
from trezor import config, ui

from . import HomescreenBase


async def homescreen() -> None:
    await Homescreen()


class Homescreen(HomescreenBase):
    def __init__(self) -> None:
        super().__init__()
        if not storage.is_initialized():
            self.label = "Go to trezor.io/start"

    def render_warning(self) -> None:
        if storage.is_initialized() and storage.device.no_backup():
            ui.header_error("SEEDLESS")
        elif storage.is_initialized() and storage.device.unfinished_backup():
            ui.header_error("BACKUP FAILED!")
        elif storage.is_initialized() and storage.device.needs_backup():
            ui.header_warning("NEEDS BACKUP!")
        elif storage.is_initialized() and not config.has_pin():
            ui.header_warning("PIN NOT SET!")
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)

    def on_render(self) -> None:
        self.render_warning()
        self.render_homescreen()
