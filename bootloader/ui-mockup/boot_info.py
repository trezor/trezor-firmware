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

# header
# ui.display.bar(0, 0, 240, 30, ui.ORANGE, ui.BLACK, 4)
# ui.display.bar(0, 10, 240, 20, ui.ORANGE)
# ui.display.text(10, 23, 'Bootloader info', ui.BOLD, ui.WHITE, ui.ORANGE)

image = res.load('./res/sl_logo.toif')
ui.display.image(60, 10, image)

ui.display.text_center(120, 148, "SatoshiLabs firmware", 1, ui.WHITE, ui.BLACK)
ui.display.text_center(120, 171, "v0.1.1", 1, ui.GREY, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=DEFAULT_BUTTON, active_style=DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    ui.display.refresh()