#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui
from trezor.ui import button

CANCEL_BUTTON = {
    'bg-color': ui.RED,
    'fg-color': ui.LIGHT_RED,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
}
CANCEL_BUTTON_ACTIVE = {
    'bg-color': ui.RED,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
}

ui.display.backlight(255)

# background frame
# ui.display.bar(0, 10, 240, 240 - 50, ui.LIGHT_RED)
# ui.display.bar(3, 3, 234, 240 - 54, ui.BLACK)

# header
ui.display.bar(0, 0, 240, 30, ui.LIGHT_RED, ui.BLACK, 4)
ui.display.bar(0, 10, 240, 20, ui.LIGHT_RED)
ui.display.text(10, 23, 'Unsigned firmware!', ui.BOLD, ui.WHITE, ui.LIGHT_RED)

# content
ui.display.text(10, 60, 'Check your fingeprint', ui.NORMAL, ui.WHITE, ui.BLACK)

# fingerprint box
ui.display.bar(10, 76, 220, 105, ui.DARK_GREY)
s = 103
ui.display.text(15, s, '5764715dbcf8ed88', ui.MONO, ui.GREY, ui.DARK_GREY)
ui.display.text(15, s + 1 * 23, 'bc0ae1c2f715277f', ui.MONO, ui.GREY, ui.DARK_GREY)
ui.display.text(15, s + 2 * 23, '22b67f26c15e1f75', ui.MONO, ui.GREY, ui.DARK_GREY)
ui.display.text(15, s + 3 * 23, '43b2b44913b5c255', ui.MONO, ui.GREY, ui.DARK_GREY)

cancel = button.Button((0, 240 - 48, 240, 48), 'Proceed anyway', normal_style=CANCEL_BUTTON, active_style=CANCEL_BUTTON_ACTIVE)
cancel.render()

while True:
    ui.display.refresh()