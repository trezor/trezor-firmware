#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

from trezor import ui, res

ui.display.backlight(255)


# header
ui.display.bar(0, 0, 240, 32, ui.ORANGE, ui.BLACK, 4)
ui.display.bar(0, 10, 240, 22, ui.ORANGE)

image = res.load('./res/bootloader.toig')
ui.display.icon(8, 4, image, ui.ORANGE, ui.WHITE)

ui.display.text(35, 23, 'Installing firmware', ui.BOLD, ui.WHITE, ui.ORANGE)

ui.display.text_center(120, 192 + 32, "In progress ...", 1, ui.WHITE, ui.BLACK)

p = 0
while True:

    ui.display.loader(p, ui.BLUE, ui.BLACK)
    ui.display.text_center(120, 240 // 2 + 14 // 2, "%d%%" % (p // 10), 2, ui.WHITE, ui.BLACK)

    ui.display.refresh()

    p = (p + 1) % 1000
