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

# Reallocated once per session and shared between all wire interfaces.
# Acquired by the first call to `CodecContext.read_from_wire()`.
WIRE_BUFFER_PROVIDER = wire.BufferProvider(8192)

# initialize the wire codec over USB
wire.setup(usb.iface_wire, WIRE_BUFFER_PROVIDER)

if utils.USE_BLE:
    import trezorble as ble

    # initialize the wire codec over BLE
    wire.setup(ble.interface, WIRE_BUFFER_PROVIDER)

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
