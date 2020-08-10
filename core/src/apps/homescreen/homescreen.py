import storage
import storage.device
from trezor import config, ui

from . import HomescreenBase


async def homescreen() -> None:
    await Homescreen()


class Homescreen(HomescreenBase):
    def __init__(self) -> None:
        super().__init__()
        if not storage.device.is_initialized():
            self.label = "Go to trezor.io/start"

    def on_render(self) -> None:
        # warning bar on top
        if storage.device.is_initialized() and storage.device.no_backup():
            ui.header_error("SEEDLESS")
        elif storage.device.is_initialized() and storage.device.unfinished_backup():
            ui.header_error("BACKUP FAILED!")
        elif storage.device.is_initialized() and storage.device.needs_backup():
            ui.header_warning("NEEDS BACKUP!")
        elif storage.device.is_initialized() and not config.has_pin():
            ui.header_warning("PIN NOT SET!")
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)

        # homescreen with shifted avatar and text on bottom
        ui.display.avatar(48, 48 - 10, self.image, ui.WHITE, ui.BLACK)
        ui.display.text_center(ui.WIDTH // 2, 220, self.label, ui.BOLD, ui.FG, ui.BG)
