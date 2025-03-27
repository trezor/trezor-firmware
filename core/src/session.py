# isort: skip_file
from trezor import log, loop, utils, wire, workflow, io

import apps.base
import usb
from typing import Generator


class BleInterface:

    RX_PACKET_LEN = io.ble.RX_PACKET_LEN
    TX_PACKET_LEN = io.ble.TX_PACKET_LEN

    def iface_num(self) -> int:
        return io.BLE

    def write(self, msg: bytes) -> int:
        return io.ble.write(msg)

    def read(self, buffer: bytearray, offset: int = 0) -> int:
        return io.ble.read(buffer, offset)


# interface used for trezor wire protocol
iface_ble = BleInterface()


def ble_events() -> Generator:
    from trezor import io

    x = loop.wait(io.BLE_EVENT)
    while True:
        # Using `yield` instead of `await` to avoid allocations.
        event = yield x
        print(f"ble_event {event}")


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
# wire.setup(usb.iface_wire)
wire.setup(BleInterface())
loop.schedule(ble_events())

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
