import storage.device
from trezor import io, res, ui

if False:
    from typing import Any, Coroutine


class HomescreenBase(ui.Layout):
    def __init__(self) -> None:
        self.repaint = True

        self.label = storage.device.get_label() or "My Trezor"
        self.image = storage.device.get_homescreen() or res.load(
            "apps/homescreen/res/bg.toif"
        )

    def render_homescreen(self) -> None:
        ui.display.avatar(48, 48 - 10, self.image, ui.WHITE, ui.BLACK)
        ui.display.text_center(ui.WIDTH // 2, 220, self.label, ui.BOLD, ui.FG, ui.BG)

    def dispatch(self, event: int, x: int, y: int) -> None:
        if event is ui.RENDER and self.repaint:
            self.repaint = False
            self.on_render()
        elif event is io.TOUCH_END:
            self.on_touch_end(x, y)

    def __iter__(self) -> Coroutine[Any, Any, ui.ResultValue]:
        # called whenever `await homescreen` is invoked.
        # we want to repaint once after that and then never again
        self.repaint = True
        return super().__iter__()
