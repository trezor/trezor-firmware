import storage.device
from trezor import res, ui


class HomescreenBase(ui.Layout):
    def __init__(self) -> None:
        super().__init__()
        self.label = storage.device.get_label() or "My Trezor"
        self.image = storage.device.get_homescreen() or res.load(
            "apps/homescreen/res/bg.toif"
        )
