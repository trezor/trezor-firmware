#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res
from trezor.ui import button

CONFIRM_BUTTON = {
    'bg-color': ui.BLUE,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.BLACK,
}
CONFIRM_BUTTON_ACTIVE = {
    'bg-color': ui.BLUE,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.BLACK,
}

ui.display.backlight(255)

# header
ui.display.bar(0, 0, 240, 32, ui.ORANGE, ui.BLACK, 4)
ui.display.bar(0, 10, 240, 22, ui.ORANGE)

image = res.load('./res/bootloader.toig')
ui.display.icon(8, 4, image, ui.ORANGE, ui.WHITE)

ui.display.text(35, 23, 'Install new firmware', ui.BOLD, ui.WHITE, ui.ORANGE)

# content
ui.display.text(10, 53, 'Warning!', ui.BOLD, ui.WHITE, ui.BLACK)
ui.display.text(10, 83, 'Never do this without', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 106, 'your recovery card and', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 129, 'due to different vendor', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 151, 'your storage will be', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 174, 'wipped!', ui.NORMAL, ui.WHITE, ui.BLACK)

confirm = button.Button((0, 240 - 48, 240, 48), 'Hold to confirm', normal_style=CONFIRM_BUTTON, active_style=CONFIRM_BUTTON_ACTIVE)
confirm.render()

while True:
    ui.display.refresh()