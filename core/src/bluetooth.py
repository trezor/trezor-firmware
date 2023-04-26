from trezorio import ble


class BleInterfaceInternal:
    def iface_num(self) -> int:
        return 16

    def write(self, msg: bytes) -> int:
        return ble.write_int(self, msg)


class BleInterfaceExternal:
    def iface_num(self) -> int:
        return 17

    def write(self, msg: bytes) -> int:
        return ble.write_ext(self, msg)


# interface used for trezor wire protocol
iface_ble_int = BleInterfaceInternal()
iface_ble_ext = BleInterfaceExternal()
