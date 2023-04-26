from micropython import const
from mutex import Mutex

from trezor import log, loop, utils, wire, workflow

import apps.base
import usb

_PROTOBUF_BUFFER_SIZE = const(8192)
WIRE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)


apps.base.boot()

mutex = Mutex()

if not utils.BITCOIN_ONLY and usb.ENABLE_IFACE_WEBAUTHN:
    import apps.webauthn

    apps.webauthn.boot(mutex)

if __debug__:
    import apps.debug

    apps.debug.boot()


# run main event loop and specify which screen is the default
apps.base.set_homescreen()
workflow.start_default()


mutex.add(usb.iface_wire.iface_num())
mutex.add(usb.iface_debug.iface_num())

# initialize the wire codec
wire.setup(usb.iface_wire, WIRE_BUFFER, wire.common_find_handler, mutex=mutex)

if __debug__:
    PROTOBUF_BUFFER_SIZE_DEBUG = 1024
    WIRE_BUFFER_DEBUG = bytearray(PROTOBUF_BUFFER_SIZE_DEBUG)

    wire.setup(
        usb.iface_debug,
        WIRE_BUFFER_DEBUG,
        wire.common_find_handler,
        is_debug_session=True,
    )

if utils.USE_BLE:
    import bluetooth

    BLE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)
    ble_find_handler = wire.MessageHandler()
    ble_find_handler.register_find_handler(bluetooth.int_find_handler)

    mutex.add(bluetooth.iface_ble_int.iface_num())
    mutex.add(bluetooth.iface_ble_ext.iface_num())
    wire.setup(bluetooth.iface_ble_int, BLE_BUFFER, ble_find_handler, mutex=mutex)
    wire.setup(
        bluetooth.iface_ble_ext, BLE_BUFFER, wire.common_find_handler, mutex=mutex
    )


loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
