# isort: skip_file
from trezor import log, loop, utils, wire, workflow

import apps.base
from apps.common import lock_manager
import usb

apps.base.boot()

if not utils.BITCOIN_ONLY and usb.ENABLE_IFACE_WEBAUTHN:
    import apps.webauthn

    apps.webauthn.boot()

if __debug__:
    import apps.debug

    apps.debug.boot()

# run main event loop and specify which screen is the default
lock_manager.boot()
workflow.start_default()

if utils.USE_BLE:
    import trezorble as ble

    # initialize the wire codec over USB & BLE
    wire.setup(usb.iface_wire, ble.interface)
else:
    # initialize the wire codec over USB
    wire.setup(usb.iface_wire)

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
