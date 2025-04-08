from typing import *



# upymod/modtrezorio/modtrezorio-ble.h
def erase_bonds() -> bool:
    """
    Erases all BLE bonds
    """


# upymod/modtrezorio/modtrezorio-ble.h
def unpair() -> bool:
    """
    Erases bond for current connection, if any
    """


# upymod/modtrezorio/modtrezorio-ble.h
def start_comm() -> bool:
    """
    Start communication with BLE chip
    """


# upymod/modtrezorio/modtrezorio-ble.h
def start_advertising(whitelist: bool, name: str | None) -> bool:
    """
    Start advertising
    """


# upymod/modtrezorio/modtrezorio-ble.h
def stop_advertising() -> bool:
    """
    Stop advertising
    """


# upymod/modtrezorio/modtrezorio-ble.h
def disconnect() -> bool:
    """
    Disconnect BLE
    """


# upymod/modtrezorio/modtrezorio-ble.h
def peer_count() -> int:
    """
    Get peer count (number of bonded devices)
    """


# upymod/modtrezorio/modtrezorio-ble.h
def allow_pairing(code: int) -> bool:
    """
    Accept BLE pairing request. Code must match the one received with
    BLE_PAIRING_REQUEST event.
    """


# upymod/modtrezorio/modtrezorio-ble.h
def reject_pairing() -> bool:
    """
    Reject BLE pairing request
    """


# upymod/modtrezorio/modtrezorio-ble.h
class BleInterface:
    """
    BLE interface wrapper.
    """

    def __init__(
        self,
    ) -> None:
        """
        Initialize BLE interface.
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: bytes) -> int:
        """
        Sends message over BLE
        """

    def read(self, buf: bytearray, offset: int = 0) -> int:
        """
        Reads message using BLE (device).
        """
    RX_PACKET_LEN: int
    """Length of one BLE RX packet."""
    TX_PACKET_LEN: int
    """Length of one BLE TX packet."""
