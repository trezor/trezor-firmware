from trezor import ui
from trezor import loop
from trezor import layout

def layout_homescreen():
    print("Homescreen layout!")

    from apps import playground
    loop.call_later(5 * 1000000, layout.change(playground.layout_tap_to_confirm('1BitkeyP2nDd5oa64x7AjvBbbwST54W5Zmx2', 110.126967, 'BTC')))

    ui.display.bar(0, 0, 240, 240, ui.WHITE)

    f = open('apps/homescreen/trezor.toig', 'r')

    def func(foreground):
        f.seek(0)
        ui.display.icon(0, 0, f.read(), foreground, ui.BLACK)

    yield from ui.animate_pulse(func, SPEED=400000, BASE_COLOR=(0xff, 0xff, 0xff), MIN_COLOR=0xaa, MAX_COLOR=0xff)
