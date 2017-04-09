#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui
from trezor.ui import button
from bl_common import bl_header

ui.display.clear()
ui.display.backlight(255)

# header
bl_header('Install new firmware')

# content
ui.display.text(10, 53, 'Warning!', ui.BOLD, ui.WHITE, ui.BLACK)
ui.display.text(10, 83, 'Never do this without', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 106, 'your recovery card and', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 129, 'due to different vendor', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 151, 'your storage will be', ui.NORMAL, ui.WHITE, ui.BLACK)
ui.display.text(10, 174, 'wipped!', ui.NORMAL, ui.WHITE, ui.BLACK)

confirm = button.Button((0, 240 - 48, 240, 48), 'Hold to confirm', normal_style=button.CONFIRM_BUTTON, active_style=button.CONFIRM_BUTTON_ACTIVE)
confirm.render()

while True:
    ui.display.refresh()
