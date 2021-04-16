import storage.cache
from trezor import loop, res, ui, wire

from . import HomescreenBase


async def lockscreen() -> None:
    from apps.common.request_pin import can_lock_device
    from apps.base import unlock_device

    # Only show the lockscreen UI if the device can in fact be locked.
    if can_lock_device():
        await Lockscreen()
    # Otherwise proceed directly to unlock() call. If the device is already unlocked,
    # it should be a no-op storage-wise, but it resets the internal configuration
    # to an unlocked state.
    try:
        await unlock_device()
    except wire.PinCancelled:
        pass


class Lockscreen(HomescreenBase):
    BACKLIGHT_LEVEL = ui.BACKLIGHT_LOW
    RENDER_SLEEP = loop.SLEEP_FOREVER
    RENDER_INDICATOR = storage.cache.LOCKSCREEN_ON

    def __init__(self, bootscreen: bool = False) -> None:
        if bootscreen:
            self.BACKLIGHT_LEVEL = ui.BACKLIGHT_NORMAL
            self.lock_label = "Not connected"
            self.tap_label = "Tap to connect"
        else:
            self.lock_label = "Locked"
            self.tap_label = "Tap to unlock"

        super().__init__()

    def do_render(self) -> None:
        # homescreen with label text on top
        ui.display.text_center(
            ui.WIDTH // 2, 35, self.label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )
        ui.display.avatar(48, 48, self.get_image(), ui.WHITE, ui.BLACK)

        # lock bar
        ui.display.bar_radius(40, 100, 160, 40, ui.TITLE_GREY, ui.BG, 4)
        ui.display.bar_radius(42, 102, 156, 36, ui.BG, ui.TITLE_GREY, 4)
        ui.display.text_center(
            ui.WIDTH // 2, 128, self.lock_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )

        # "tap to unlock"
        ui.display.text_center(
            ui.WIDTH // 2 + 10, 220, self.tap_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        )
        ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.TITLE_GREY, ui.BG)

    def on_touch_end(self, _x: int, _y: int) -> None:
        raise ui.Result(None)
