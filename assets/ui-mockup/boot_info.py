#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res
from trezor.ui import button

ui.display.clear()
ui.display.backlight(255)

image = res.load('./res/sl_logo.toif')
ui.display.image(60, 10, image)

ui.display.text_center(120, 160, "SatoshiLabs", 1, ui.WHITE, ui.BLACK)
ui.display.text_center(120, 183, "v0.1.1", 1, ui.GREY, ui.BLACK)

reboot = button.Button((0, 240 - 48, 240, 48), 'Reboot', normal_style=button.DEFAULT_BUTTON, active_style=button.DEFAULT_BUTTON_ACTIVE)
reboot.render()

while True:
    ui.display.refresh()
