from typing import *


# upymod/modtrezorio/modtrezorio-ble.h
def write(msg: bytes) -> int:
    """
    Sends message over BLE
    """


# upymod/modtrezorio/modtrezorio-ble.h
def read(buf: bytearray, offset: int = 0) -> int:
    """
    Reads message using BLE (device).
    """


# upymod/modtrezorio/modtrezorio-ble.h
def erase_bonds() -> None:
    """
    Erases all BLE bonds
    """


# upymod/modtrezorio/modtrezorio-ble.h
def start_comm() -> None:
    """
    Start communication with BLE chip
    """


# upymod/modtrezorio/modtrezorio-ble.h
def start_advertising(whitelist: bool) -> None:
    """
    Start advertising
    """


# upymod/modtrezorio/modtrezorio-ble.h
def stop_advertising(whitelist: bool) -> None:
    """
    Stop advertising
    """


# upymod/modtrezorio/modtrezorio-ble.h
def disconnect() -> None:
    """
    Disconnect BLE
    """
RX_PACKET_LEN: ClassVar[int]
"""Length of one BLE RX packet."""
TX_PACKET_LEN: ClassVar[int]
"""Length of one BLE TX packet."""
