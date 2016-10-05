#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res
from bl_common import bl_header

ui.display.clear()
ui.display.backlight(255)

# header
bl_header('Installing firmware')

ui.display.text_center(120, 192 + 32, "In progress ...", 1, ui.WHITE, ui.BLACK)

p = 0
while True:

    ui.display.loader(p, ui.BLUE, ui.BLACK)
    ui.display.text_center(120, 240 // 2 + 14 // 2, "%d%%" % (p // 10), 2, ui.WHITE, ui.BLACK)

    if hasattr(ui.display, 'refresh'): ui.display.refresh()

    p = (p + 1) % 1000
