import storage.device
from trezor import loop, res, ui


class HomescreenBase(ui.Layout):
    RENDER_SLEEP = loop.SLEEP_FOREVER

    def __init__(self) -> None:
        self.repaint = True

        self.label = storage.device.get_label() or "My Trezor"
        self.image = storage.device.get_homescreen() or res.load(
            "apps/homescreen/res/bg.toif"
        )

    def render_homescreen(self) -> None:
        ui.display.avatar(48, 48 - 10, self.image, ui.WHITE, ui.BLACK)
        ui.display.text_center(ui.WIDTH // 2, 220, self.label, ui.BOLD, ui.FG, ui.BG)
