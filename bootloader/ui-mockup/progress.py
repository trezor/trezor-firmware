#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui

ui.display.backlight(255)

ui.display.bar(0, 192, 240, 48, ui.ORANGE)
ui.display.text_center(120, 192 + 32, "Installing Update", 1, ui.WHITE, ui.ORANGE)

p = 0
while True:

    ui.display.loader(p, ui.BLUE, ui.BLACK)
    ui.display.text_center(120, 192 // 2 + 14 // 2, "%d%%" % (p // 10), 2, ui.WHITE, ui.BLACK)

    ui.display.refresh()

    p = (p + 1) % 1000
