from trezor import ui
from trezor.ui import utils as ui_utils
from trezor.ui.swipe import Swipe
from trezor import loop


def swipe_to_change_orientation():
    while True:
        degrees = yield from Swipe().wait()
        ui.display.orientation(degrees)


def layout_homescreen():
    print("Homescreen layout!")

    f = open('apps/homescreen/trezor.toig', 'rb')

    def func(foreground):
        f.seek(0)
        ui.display.icon(0, 0, f.read(), foreground, ui_utils.BLACK)

    orientation = swipe_to_change_orientation()
    animation = ui_utils.animate_pulse(func, ui_utils.WHITE, ui_utils.GREY, speed=400000)
    timeout = loop.Sleep(5000 * 1000)

    yield loop.Wait([
        orientation,
        animation,
        timeout
    ])

    from apps import playground
    return playground.layout_tap_to_confirm('1BitkeyP2nDd5oa64x7AjvBbbwST54W5Zmx2', 110.126967, 'BTC')
