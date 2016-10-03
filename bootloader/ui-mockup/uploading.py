#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui

ui.display.backlight(255)

ui.display.text_center(120, 192 + 32, "Uploading firmware", 1, ui.WHITE, ui.BLACK)

p = 0
while True:

    ui.display.loader(p, ui.BLUE, ui.BLACK)
    ui.display.text_center(120, 192 // 2 + 14 // 2, "%d%%" % (p // 10), 2, ui.WHITE, ui.BLACK)

    ui.display.refresh()

    p = (p + 1) % 1000
