from ubinascii import hexlify
from trezor import ui, loop, res
from trezor.utils import unimport_gen
from trezor.crypto import random
from . import knownapps

ids = list(knownapps.knownapps.keys())
random.shuffle(ids)

appid = ids[0]
action = 'Register'

@unimport_gen
def layout_u2f():

    if appid in knownapps.knownapps:
        appname = knownapps.knownapps[appid]
        appicon = res.load('apps/fido_u2f/res/u2f_%s.toif' % appname.lower().replace(' ', '_'))
    else:
        appname = hexlify(appid[:4]) + '...' + hexlify(appid[-4:])
        appicon = res.load('apps/fido_u2f/res/u2f_unknown.toif')

    # paint background black
    ui.display.bar(0, 0, 240, 240, ui.BLACK)

    # top header bar
    ui.display.text(10, 28, 'U2F Login', ui.BOLD, ui.PM_BLUE, ui.BLACK)

    # content
    ui.display.text_center(120, 70, '%s:' % action, ui.BOLD, ui.GREY, ui.BLACK)
    ui.display.image((240 - 64) // 2, 90, appicon)
    ui.display.text_center(120, 185, appname, ui.MONO, ui.WHITE, ui.BLACK)

    yield loop.Wait([])
