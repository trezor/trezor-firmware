from trezor import ui, dispatcher, loop, res, wire
from trezor.ui.swipe import Swipe
from trezor.utils import unimport_gen


def swipe_to_rotate():
    while True:
        degrees = yield from Swipe(absolute=True).wait()
        ui.display.orientation(degrees)


def animate_logo():
    def func(foreground):
        ui.display.icon(0, 0, res.load('apps/homescreen/res/trezor.toig'), foreground, ui.BLACK)
    yield from ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)


@unimport_gen
def layout_homescreen(initialize_msg=None):
    if initialize_msg is not None:
        from trezor.messages.Features import Features
        features = Features()
        features.revision = 'deadbeef'
        features.bootloader_hash = 'deadbeef'
        features.device_id = 'DEADBEEF'
        features.coins = []
        features.imported = False
        features.initialized = False
        features.label = 'My TREZOR'
        features.major_version = 2
        features.minor_version = 0
        features.patch_version = 0
        features.pin_cached = False
        features.pin_protection = True
        features.passphrase_cached = False
        features.passphrase_protection = False
        features.vendor = 'bitcointrezor.com'
        yield from wire.write(features)
    yield loop.Wait([dispatcher.dispatch(),
                     swipe_to_rotate(),
                     animate_logo()])
