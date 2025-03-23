from trezorio import BLE, ble


class BleInterface:

    RX_PACKET_LEN = ble.RX_PACKET_LEN
    TX_PACKET_LEN = ble.TX_PACKET_LEN

    def iface_num(self) -> int:
        return BLE

    def write(self, msg: bytes) -> int:
        return ble.write(msg)

    def read(self, buffer: bytearray, offset: int = 0) -> int:
        return ble.read(buffer, offset)


# interface used for trezor wire protocol
iface_ble = BleInterface()
