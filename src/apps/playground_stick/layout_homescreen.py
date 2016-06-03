from trezor import ui
from trezor import loop
from trezor import res

c = ui.rgbcolor(0x20, 0x98, 0xD1)

def layout_homescreen():

    ui.display.bar(0, 0, 240, 48 * 4, ui.BLACK)
    ui.display.bar(0, 48 * 4, 240, 48, c, ui.BLACK)
    ui.display.text_center(120, 240 - 18, 'Hold to confirm', ui.BOLD, ui.WHITE, c)
    p = 0

    def func(foreground):
        ui.display.loader(p, c, 0, res.load('apps/playground_stick/res/fingerprint.toig'), foreground)
        p = (p + 10) % 1000

    animation = ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)

    yield from animation
