#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui
from trezor.ui import button
from bl_common import bl_header

ui.display.clear()
ui.display.backlight(255)

# background frame
ui.display.bar(0, 10, 240, 240 - 50, ui.LIGHT_RED)
ui.display.bar(3, 3, 234, 240 - 54, ui.BLACK)

# header
bl_header('Install failed')

# content
ui.display.text(10, 53, 'Some error happend', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 79, 'Sorry, try again maybe?', ui.NORMAL, ui.WHITE, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=button.DEFAULT_BUTTON, active_style=button.DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    ui.display.refresh()
