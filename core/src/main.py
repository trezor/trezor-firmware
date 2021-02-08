# isort:skip_file
import gc
from trezor import utils

mods = utils.unimport_begin()
import boot
del boot
utils.unimport_end(mods)

import usb
usb.bus.open()

state = {}
mods = utils.unimport_begin()

while True:
    import session
    session.handle(state)
    del session
    utils.unimport_end(mods)
    print("reboot", gc.mem_free(), gc.mem_frag())