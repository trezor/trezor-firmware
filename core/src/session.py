# isort: skip_file
from micropython import const

from trezor import log, loop, utils, wire, workflow

import apps.base
import usb

_PROTOBUF_BUFFER_SIZE = const(8192)
WIRE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)


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
wire.setup(usb.iface_wire, WIRE_BUFFER)

if utils.USE_BLE:
    import bluetooth

    BLE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)

    wire.setup(bluetooth.iface_ble, BLE_BUFFER)


# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
