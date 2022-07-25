import storage.cache
from trezor import loop, res, ui, utils, wire

from . import HomescreenBase


async def lockscreen() -> None:
    """Is model-specific."""
    from apps.common.request_pin import can_lock_device
    from apps.base import unlock_device

    # Only show the lockscreen UI if the device can in fact be locked.
    if can_lock_device():
        await get_lockscreen()
    # Otherwise proceed directly to unlock() call. If the device is already unlocked,
    # it should be a no-op storage-wise, but it resets the internal configuration
    # to an unlocked state.
    try:
        await unlock_device()
    except wire.PinCancelled:
        pass


def get_lockscreen(bootscreen: bool = False) -> HomescreenBase:
    """Return appropriate lockscreen for the current model."""
    if utils.MODEL in ("T",):
        return LockscreenModelT(bootscreen)
    elif utils.MODEL in ("R",):
        return LockscreenModelR(bootscreen)
    elif utils.MODEL in ("1",):
        return LockscreenModel1(bootscreen)
    else:
        raise Exception("Unknown model")


class LockscreenModelR(HomescreenBase):
    BACKLIGHT_LEVEL = ui.BACKLIGHT_LOW
    RENDER_SLEEP = loop.SLEEP_FOREVER
    RENDER_INDICATOR = storage.cache.LOCKSCREEN_ON

    def __init__(self, bootscreen: bool = False) -> None:
        if bootscreen:
            self.BACKLIGHT_LEVEL = ui.BACKLIGHT_NORMAL
            self.lock_label = "Not connected"
            self.tap_label = "Click to connect"
        else:
            self.lock_label = "Locked"
            self.tap_label = "Click to unlock"

        super().__init__()

    def do_render(self) -> None:
        ui.display.text_center(
            ui.WIDTH // 2, 9, self.label.upper(), ui.MONO, ui.FG, ui.BG
        )
        ui.display.icon(0, 11, self.get_avatar(), ui.style.FG, ui.style.BG)

        # Lock icon placement depends on the lock_label text
        lock_icon = ui.res.load("trezor/res/model_r/lock.toif")
        if self.lock_label == "Not connected":
            ui.display.icon(13, 90, lock_icon, ui.style.FG, ui.style.BG)
        else:
            ui.display.icon(38, 90, lock_icon, ui.style.FG, ui.style.BG)

        ui.display.text_center(
            ui.WIDTH // 2 + 10, 100, self.lock_label.upper(), ui.NORMAL, ui.FG, ui.BG
        )
        ui.display.text_center(
            ui.WIDTH // 2, 115, self.tap_label.upper(), ui.MONO, ui.FG, ui.BG
        )

    def on_button_released(self, _x: int) -> None:
        """Going to the PIN screen after pressing any button."""
        raise ui.Result(None)


class LockscreenModel1(HomescreenBase):
    BACKLIGHT_LEVEL = ui.BACKLIGHT_LOW
    RENDER_SLEEP = loop.SLEEP_FOREVER
    RENDER_INDICATOR = storage.cache.LOCKSCREEN_ON

    def __init__(self, bootscreen: bool = False) -> None:
        if bootscreen:
            self.BACKLIGHT_LEVEL = ui.BACKLIGHT_NORMAL
            self.lock_label = "Not connected"
            self.tap_label = "Click to connect"
        else:
            self.lock_label = "Locked"
            self.tap_label = "Click to unlock"

        super().__init__()

    def do_render(self) -> None:
        ui.header_warning(self.lock_label)
        ui.display.icon(33, 14, self.get_avatar(), ui.style.FG, ui.style.BG)
        ui.display.text_center(ui.WIDTH // 2, 60, self.label, ui.BOLD, ui.FG, ui.BG)

    def on_button_released(self, _x: int) -> None:
        """Going to the PIN screen after pressing any button."""
        raise ui.Result(None)


class LockscreenModelT(HomescreenBase):
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
        ui.display.avatar(48, 48, self.get_avatar(), ui.WHITE, ui.BLACK)

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
        """Going to the PIN screen after tapping the display."""
        raise ui.Result(None)
