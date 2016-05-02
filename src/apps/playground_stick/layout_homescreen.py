from trezor import ui
from trezor import loop


def layout_homescreen():

    # ui.display.bar(0, 0, 240, 240, ui.WHITE)

    f = open('apps/playground_stick/trezor.toig', 'r')

    def func(foreground):
        f.seek(0)
        ui.display.icon(0, 0, f.read(), foreground, ui.BLACK)

    animation = ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)

    yield from animation
