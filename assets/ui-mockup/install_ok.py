#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui
from trezor.ui import button
from bl_common import bl_header

ui.display.clear()
ui.display.backlight(255)

# header
bl_header('Install done')

# content
# content
ui.display.text(10, 53, 'Success!', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 79, 'Time to reboot', ui.NORMAL, ui.WHITE, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=button.DEFAULT_BUTTON, active_style=button.DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    ui.display.refresh()
