import storage.device
from trezor import io, loop, res, ui


class HomescreenBase(ui.Layout):
    RENDER_SLEEP = loop.SLEEP_FOREVER

    def __init__(self) -> None:
        self.label = storage.device.get_label() or "My Trezor"
        self.image = storage.device.get_homescreen() or res.load(
            "apps/homescreen/res/bg.toif"
        )
        self.repaint = True

    def on_tap(self) -> None:
        """Called when the user taps the screen."""
        pass

    def dispatch(self, event: int, x: int, y: int) -> None:
        if event is ui.REPAINT:
            self.repaint = True
        elif event is ui.RENDER and self.repaint:
            self.repaint = False
            self.on_render()
        elif event is io.TOUCH_END:
            self.on_tap()
