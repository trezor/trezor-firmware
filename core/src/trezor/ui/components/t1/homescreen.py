import storage
import storage.cache
import storage.device
from trezor import config, ui
from trezor.ui.components.common.homescreen import HomescreenBase

from . import header


class Homescreen(HomescreenBase):
    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()

    def do_render(self) -> None:
        # TODO: icons
        if storage.device.is_initialized() and storage.device.no_backup():
            header("SEEDLESS")
        elif storage.device.is_initialized() and storage.device.unfinished_backup():
            header("BACKUP FAILED")
        elif storage.device.is_initialized() and storage.device.needs_backup():
            header("BACKUP IS NEEDED")
        elif storage.device.is_initialized() and not config.has_pin():
            header("PIN NOT SET")
        elif storage.device.get_experimental_features():
            header("EXPERIMENTAL MODE")
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)

        # TODO: avatar
        # TODO: ui.BOLD fits few characters, break into multiple lines?
        if not storage.device.is_initialized():
            label = "Go to trezor.io/start"
            font = ui.NORMAL
        else:
            label = self.label
            font = ui.BOLD
        ui.display.text_center(ui.WIDTH // 2, ui.HEIGHT - 2, label, font, ui.FG, ui.BG)
