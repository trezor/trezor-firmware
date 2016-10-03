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
ui.display.text(10, 30, 'Firmware upload', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
ui.display.text(10, 60, 'Install new firmware?', ui.BOLD, ui.WHITE, ui.BLACK)
ui.display.text(10, 90, 'Never do this without', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 120, 'your recovery card!', ui.NORMAL, ui.WHITE, ui.BLACK)

confirm = button.Button((121, 240 - 48, 119, 48), 'Confirm', normal_style=CONFIRM_BUTTON, active_style=CONFIRM_BUTTON_ACTIVE)
confirm.render()
cancel = button.Button((0, 240 - 48, 119, 48), 'Cancel', normal_style=CANCEL_BUTTON, active_style=CANCEL_BUTTON_ACTIVE)
cancel.render()

while True:
    ui.display.refresh()