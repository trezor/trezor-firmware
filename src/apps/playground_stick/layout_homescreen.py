from trezor import ui
from trezor import loop

f = open('apps/playground_stick/fingerprint.toig', 'rb')
c = ui.rgbcolor(0x20, 0x98, 0xD1)

def layout_homescreen():

    ui.display.bar(0, 0, 240, 48 * 4, ui.BLACK)
    ui.display.bar(0, 48 * 4, 240, 48, c)
    ui.text_center(120, 240 - 18, 'Hold to confirm', 2, ui.WHITE, c)
    p = 0

    def func(foreground):
        f.seek(0)
        ui.display.loader(p, c, 0, f.read(), foreground)
        p = (p + 10) % 1000

    animation = ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)

    yield from animation
