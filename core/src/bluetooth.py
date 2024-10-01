from trezorio import BLE, ble


class BleInterface:
    def iface_num(self) -> int:
        return BLE

    def write(self, msg: bytes) -> int:
        return ble.write(msg)

    def read(self, buffer: bytes, offset: int = 0) -> int:
        return ble.read(buffer, offset)


# interface used for trezor wire protocol
iface_ble = BleInterface()
