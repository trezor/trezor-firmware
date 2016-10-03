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
ui.display.image(60, 0, image)


ui.display.text_center(120, 144, "SatoshiLabs firmware", 1, ui.WHITE, ui.BLACK)
ui.display.text_center(120, 164, "v0.1.1", 1, ui.GREY, ui.BLACK)

confirm = button.Button((0, 240 - 48, 240, 48), 'Start anyway', normal_style=CONFIRM_BUTTON, active_style=CONFIRM_BUTTON_ACTIVE)
confirm.render()

ui.display.bar(1, 1, 238, 38, ui.LIGHT_RED)
ui.display.bar(3, 3, 234, 34, ui.BLACK)
ui.display.text_center(120, 26, "Unsigned firmware!", 1, ui.LIGHT_RED, ui.BLACK)


while True:
    ui.display.refresh()