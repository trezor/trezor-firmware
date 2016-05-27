from trezor import ui
from trezor.ui.swipe import Swipe
from trezor import loop
from trezor.res import loadres


def swipe_to_change_orientation():
    while True:
        degrees = yield from Swipe().wait()
        ui.display.orientation(degrees)


def layout_homescreen():
    print("Homescreen layout!")

    def func(foreground):
        ui.display.icon(0, 0, loadres('apps/homescreen/res/trezor.toig'), foreground, ui.BLACK)

    orientation = swipe_to_change_orientation()
    animation = ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)
    timeout = loop.Sleep(5000 * 1000)

    yield loop.Wait([
        orientation,
        animation,
        timeout
    ])

    from apps import playground
    return playground.layout_tap_to_confirm('1BitkeyP2nDd5oa64x7AjvBbbwST54W5Zmx2', 110.126967, 'BTC')
