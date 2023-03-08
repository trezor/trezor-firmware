from trezorio import ble


class BleInterface:
    def __init__(self):
        pass

    def iface_num(self) -> int:
        return 16

    def iface_type(self):
        return ble.iface_type(self)

    def write(self, msg: bytes) -> int:
        return ble.write(self, msg)


# interface used for trezor wire protocol

iface_ble = BleInterface()
