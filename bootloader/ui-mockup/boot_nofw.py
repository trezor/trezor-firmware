#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res

ui.display.backlight(255)

image = res.load('../../src/apps/homescreen/res/trezor.toig')
ui.display.icon(0, 0, image, ui.WHITE, ui.BLACK)
ui.display.bar(0, 175, 240, 48, ui.BLACK)


ui.display.text_center(120, 192 + 32, "Visit TREZOR.io/start", 1, ui.WHITE, ui.BLACK)


while True:
    ui.display.refresh()