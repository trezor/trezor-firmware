# isort: skip_file
from trezor import log, loop, utils, wire, workflow

import apps.base
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

# initialize the wire codec
wire.setup(usb.iface_wire)

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
