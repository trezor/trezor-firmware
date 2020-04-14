from trezor import ui

from . import HomescreenBase


class Lockscreen(HomescreenBase):
    def on_render(self) -> None:
        self.render_homescreen()
        self.render_lock()

    def on_touch_end(self, x: int, y: int) -> None:
        raise ui.Result(None)
