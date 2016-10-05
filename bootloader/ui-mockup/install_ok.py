#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res
from trezor.ui import button
from bl_common import bl_header

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

ui.display.clear()
ui.display.backlight(255)

# header
bl_header('Install done')

# content
# content
ui.display.text(10, 53, 'Success!', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 79, 'Time to reboot', ui.NORMAL, ui.WHITE, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=DEFAULT_BUTTON, active_style=DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    if hasattr(ui.display, 'refresh'): ui.display.refresh()
