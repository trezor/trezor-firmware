from trezor import config, res, ui

from apps.common import storage
from apps.common.storage import device as storage_device


async def homescreen() -> None:
    await Homescreen()


class Homescreen(ui.Layout):
    def __init__(self) -> None:
        self.repaint = True

    def on_render(self) -> None:
        if not self.repaint:
            return

        image = None
        if not storage.is_initialized():
            label = "Go to trezor.io/start"
        else:
            label = storage_device.get_label() or "My Trezor"
            image = storage_device.get_homescreen()

        if not image:
            image = res.load("apps/homescreen/res/bg.toif")

        if storage.is_initialized() and storage_device.no_backup():
            ui.header_error("SEEDLESS")
        elif storage.is_initialized() and storage_device.unfinished_backup():
            ui.header_error("BACKUP FAILED!")
        elif storage.is_initialized() and storage_device.needs_backup():
            ui.header_warning("NEEDS BACKUP!")
        elif storage.is_initialized() and not config.has_pin():
            ui.header_warning("PIN NOT SET!")
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)
        ui.display.avatar(48, 48 - 10, image, ui.WHITE, ui.BLACK)
        ui.display.text_center(ui.WIDTH // 2, 220, label, ui.BOLD, ui.FG, ui.BG)

        self.repaint = False
