#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res
from trezor.ui import button

DEFAULT_BUTTON = {
    'bg-color': ui.DARK_GREY,
    'fg-color': ui.GREY,
    'text-style': ui.NORMAL,
    'border-color': ui.BLACK,
}
DEFAULT_BUTTON_ACTIVE = {
    'bg-color': ui.GREY,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.GREY,
}

ui.display.backlight(255)

image = res.load('./res/sl_logo.toif')
ui.display.image(60, 0, image)

ui.display.text_center(120, 160, "SatoshiLabs firmware", 1, ui.WHITE, ui.BLACK)
ui.display.text_center(120, 183, "v0.1.1", 1, ui.GREY, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=DEFAULT_BUTTON, active_style=DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    ui.display.refresh()