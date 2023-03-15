from trezorio import ble


class BleInterface:
    def __init__(self, interface: int):
        self.interface = interface
        pass

    def iface_num(self) -> int:
        return self.interface

    def write(self, msg: bytes) -> int:
        if self.interface == 16:
            return ble.write_int(self, msg)
        if self.interface == 17:
            return ble.write_ext(self, msg)
        return 0


# interface used for trezor wire protocol

iface_ble_int = BleInterface(16)
iface_ble_ext = BleInterface(17)
