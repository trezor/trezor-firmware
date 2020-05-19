from trezor import loop, res, ui

from . import HomescreenBase


async def lockscreen() -> None:
    from apps.common.request_pin import can_lock_device
    from apps.base import unlock_device

    if can_lock_device():
        await Lockscreen()

    await unlock_device()


class Lockscreen(HomescreenBase):
    def __init__(
        self, lock_label: str = "Locked", tap_label: str = "Tap to unlock"
    ) -> None:
        self.lock_label = lock_label
        self.tap_label = tap_label
        super().__init__()

    def render_lock(self) -> None:
        ui.display.bar_radius(40, 100, 160, 40, ui.TITLE_GREY, ui.BG, 4)
        ui.display.bar_radius(42, 102, 156, 36, ui.BG, ui.TITLE_GREY, 4)
        ui.display.text_center(
            ui.WIDTH // 2, 128, self.lock_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )

        ui.display.text_center(
            ui.WIDTH // 2 + 10, 220, self.tap_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )
        ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.TITLE_GREY, ui.BG)

    def handle_rendering(self) -> loop.Task:  # type: ignore
        """Task that is rendering the layout in a busy loop.

        Copy-pasted from ui.Layout.handle_rendering with modification to set the
        backlight to a lower level while lockscreen is on, and a longer sleep because
        we never do any redrawing."""
        # Before the first render, we dim the display.
        ui.backlight_fade(ui.BACKLIGHT_DIM)
        # Clear the screen of any leftovers, make sure everything is marked for
        # repaint (we can be running the same layout instance multiple times)
        # and paint it.
        ui.display.clear()
        self.on_render()
        ui.refresh()
        ui.backlight_fade(ui.BACKLIGHT_LOW)
        # long sleep
        sleep = loop.sleep(1000 * 1000 * 1000)
        while True:
            yield sleep

    def on_render(self) -> None:
        self.render_homescreen()
        self.render_lock()

    def on_touch_end(self, x: int, y: int) -> None:
        raise ui.Result(None)
