from micropython import const
from trezorio import ble

from trezor import wire

_PROTOBUF_BUFFER_SIZE_INTERNAL = const(256)
_WIRE_BUFFER_INTERNAL = bytearray(_PROTOBUF_BUFFER_SIZE_INTERNAL)


class BleInterfaceInternal:
    IS_BLE_INTERNAL = True

    def iface_num(self) -> int:
        return ble.INTERNAL

    def write(self, msg: bytes) -> int:
        return ble.write_int(self, msg)


class BleInterfaceExternal:
    def iface_num(self) -> int:
        return ble.EXTERNAL

    def write(self, msg: bytes) -> int:
        return ble.write_ext(self, msg)


# interface used for trezor wire protocol
iface_ble_int = BleInterfaceInternal()
iface_ble_ext = BleInterfaceExternal()


def boot() -> None:
    wire.setup(iface_ble_int, buffer=_WIRE_BUFFER_INTERNAL)
    wire.setup(iface_ble_ext)
