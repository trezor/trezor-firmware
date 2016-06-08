from trezor import ui, dispatcher, loop, res, wire
from trezor.ui.swipe import Swipe
from trezor.utils import unimport_gen


def swipe_to_rotate():
    while True:
        degrees = yield from Swipe(absolute=True).wait()
        ui.display.orientation(degrees)


def animate_logo():
    def func(foreground):
        ui.display.icon(105, 200, res.load('apps/seed/res/small-arrow.toig'), foreground, ui.BLACK)
    yield from ui.animate_pulse(func, ui.WHITE, ui.BLACK, speed=190000)


@unimport_gen
def layout_seed(initialize_msg=None):
	# header title
    ui.display.text(10, 30, 'Write down your seed', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)

    ui.display.text(10, 74, '1.', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(30, 74, 'auto', ui.BOLD, ui.WHITE, ui.BLACK)

    ui.display.text(10, 104, '2.', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(30, 104, 'model', ui.BOLD, ui.WHITE, ui.BLACK)

    ui.display.text(10, 134, '3.', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(30, 134, 'rifle', ui.BOLD, ui.WHITE, ui.BLACK)

    ui.display.text(10, 164, '4.', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(30, 164, 'digital', ui.BOLD, ui.WHITE, ui.BLACK)

    yield loop.Wait([dispatcher.dispatch(),
                     swipe_to_rotate(),
                     animate_logo()])
