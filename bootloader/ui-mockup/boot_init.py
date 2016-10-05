#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res

ui.display.clear()
ui.display.backlight(255)

image = res.load('./res/monero_logo.toif')
ui.display.image(60, 32, image)

ui.display.text_center(120, 192, "MONERO", ui.BOLD, ui.WHITE, ui.BLACK)
ui.display.text_center(120, 215, "v0.1.1", 1, ui.GREY, ui.BLACK)

while True:
    if hasattr(ui.display, 'refresh'): ui.display.refresh()