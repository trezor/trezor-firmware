from trezorio import ble


class BleInterface:
    def iface_num(self) -> int:
        return 16

    def write(self, msg: bytes) -> int:
        return ble.write(self, msg)


# interface used for trezor wire protocol
iface_ble = BleInterface()
