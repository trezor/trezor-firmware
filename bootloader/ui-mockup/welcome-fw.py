#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res
from trezor.ui import button

CONFIRM_BUTTON = {
    'bg-color': ui.GREEN,
    'fg-color': ui.LIGHT_GREEN,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
}
CONFIRM_BUTTON_ACTIVE = {
    'bg-color': ui.GREEN,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
}

ui.display.backlight(255)

image = res.load('./logo.toif')
ui.display.image(60, 20, image)


ui.display.text_center(120, 174, "SatoshiLabs firmware", 1, ui.WHITE, ui.BLACK)
ui.display.text_center(120, 194, "v0.1.1", 1, ui.GREY, ui.BLACK)

while True:
    ui.display.refresh()