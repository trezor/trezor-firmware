import storage.cache
import storage.device
from trezor import res, ui


class HomescreenBase(ui.Layout):
    RENDER_INDICATOR: object | None = None

    def __init__(self) -> None:
        super().__init__()
        self.label = storage.device.get_label() or "My Trezor"
        self.image = storage.device.get_homescreen() or res.load(
            "apps/homescreen/res/bg.toif"
        )
        self.repaint = storage.cache.homescreen_shown is not self.RENDER_INDICATOR

    def on_render(self) -> None:
        if not self.repaint:
            return
        self.do_render()
        self.set_repaint(False)

    def do_render(self) -> None:
        raise NotImplementedError

    def set_repaint(self, value: bool) -> None:
        self.repaint = value
        storage.cache.homescreen_shown = None if value else self.RENDER_INDICATOR

    def _before_render(self) -> None:
        if storage.cache.homescreen_shown is not self.RENDER_INDICATOR:
            return super()._before_render()
