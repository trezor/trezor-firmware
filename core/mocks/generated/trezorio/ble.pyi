from typing import *


# upymod/modtrezorio/modtrezorio-ble.h
def write(msg: bytes) -> int:
    """
    Sends message over BLE
    """


# upymod/modtrezorio/modtrezorio-ble.h
def read(buf: bytes, offset: int = 0) -> int
    """
    Reads message using BLE (device).
    """


# upymod/modtrezorio/modtrezorio-ble.h
def erase_bonds() -> bool:
    """
    Erases all BLE bonds
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
def stop_advertising(whitelist: bool) -> bool:
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
