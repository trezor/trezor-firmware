from mutex import Mutex

from trezor import log, loop, utils, wire, workflow

import apps.base
import bluetooth
import usb

apps.base.boot()

if not utils.BITCOIN_ONLY and usb.ENABLE_IFACE_WEBAUTHN:
    import apps.webauthn

    apps.webauthn.boot()

if __debug__:
    import apps.debug

    apps.debug.boot()

# run main event loop and specify which screen is the default
apps.base.set_homescreen()
workflow.start_default()


mutex = Mutex()

mutex.add(usb.iface_wire.iface_num())
mutex.add(usb.iface_debug.iface_num())
mutex.add(bluetooth.iface_ble.iface_num())

# initialize the wire codec
wire.setup(usb.iface_wire, mutex=mutex)
if __debug__:
    wire.setup(usb.iface_debug, is_debug_session=True, mutex=mutex)
wire.setup(bluetooth.iface_ble, mutex=mutex)


loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
