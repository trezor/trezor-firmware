import storage
import storage.cache
import storage.device
from trezor import loop, ui

from . import HomescreenBase, render_header_and_refresh


class Homescreen(HomescreenBase):
    """Homescreen for model R."""

    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()

    def do_render(self) -> None:
        with render_header_and_refresh():
            # When not initialized, showing the instruction text on two lines,
            # as it cannot all fit on one line. In that case also putting
            # the icon more on the top.
            # Otherwise just showing the uppercase label in monospace.
            if not storage.device.is_initialized():
                ui.display.icon(32, 5, self.get_avatar(), ui.style.FG, ui.style.BG)
                ui.display.text_center(
                    ui.WIDTH // 2, 52, "Go to", ui.BOLD, ui.FG, ui.BG
                )
                ui.display.text_center(
                    ui.WIDTH // 2, 60, "trezor.io/start", ui.BOLD, ui.FG, ui.BG
                )
            else:
                ui.display.icon(32, 11, self.get_avatar(), ui.style.FG, ui.style.BG)
                ui.display.text_center(
                    ui.WIDTH // 2, 60, self.label.upper(), ui.MONO, ui.FG, ui.BG
                )


class Lockscreen(HomescreenBase):
    """Lockscreen for model R."""

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
        ui.display.icon(32, 11, self.get_avatar(), ui.style.FG, ui.style.BG)

        # Lock icon placement depends on the lock_label text
        lock_icon = ui.res.load("trezor/res/model_r/lock.toif")
        if self.lock_label == "Not connected":
            ui.display.icon(13, 45, lock_icon, ui.style.FG, ui.style.BG)
        else:
            ui.display.icon(38, 45, lock_icon, ui.style.FG, ui.style.BG)

        ui.display.text_center(
            ui.WIDTH // 2 + 10, 52, self.lock_label.upper(), ui.NORMAL, ui.FG, ui.BG
        )
        ui.display.text_center(
            ui.WIDTH // 2, 60, self.tap_label.upper(), ui.MONO, ui.FG, ui.BG
        )

    def on_button_released(self, _x: int) -> None:
        """Going to the PIN screen after pressing any button."""
        raise ui.Result(None)
