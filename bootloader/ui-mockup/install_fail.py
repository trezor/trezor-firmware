#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui
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

# background frame
ui.display.bar(0, 10, 240, 240 - 50, ui.LIGHT_RED)
ui.display.bar(3, 3, 234, 240 - 54, ui.BLACK)

# header
ui.display.bar(0, 0, 240, 32, ui.ORANGE, ui.BLACK, 4)
ui.display.bar(0, 10, 240, 22, ui.ORANGE)
ui.display.text(10, 23, 'Install failed', ui.BOLD, ui.WHITE, ui.ORANGE)

# content
ui.display.text(10, 53, 'Some error happend', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 79, 'Sorry, try again maybe?', ui.NORMAL, ui.WHITE, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=DEFAULT_BUTTON, active_style=DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    ui.display.refresh()