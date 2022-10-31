import storage
import storage.cache
import storage.device
from trezor import loop, ui

from . import HomescreenBase, render_header_and_refresh


class Homescreen(HomescreenBase):
    """Homescreen for model 1."""

    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        super().__init__()
        if not storage.device.is_initialized():
            self.label = "Go to trezor.io/start"

    def do_render(self) -> None:
        with render_header_and_refresh():
            ui.display.icon(33, 14, self.get_avatar(), ui.style.FG, ui.style.BG)
            ui.display.text_center(ui.WIDTH // 2, 60, self.label, ui.BOLD, ui.FG, ui.BG)


class Lockscreen(HomescreenBase):
    """Lockscreen for model 1."""

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
