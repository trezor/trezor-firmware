from typing import *


# extmod/modtrezorio/modtrezorio-ble.h
def write(self, msg: bytes) -> int:
    """
    Sends message over BLE
    """


# extmod/modtrezorio/modtrezorio-ble.h
def erase_bonds() -> None:
    """
    Erases all BLE bonds
    """


# extmod/modtrezorio/modtrezorio-ble.h
def start_comm() -> None:
    """
    Start communication with BLE chip
    """


# extmod/modtrezorio/modtrezorio-ble.h
def start_advertising(whitelist: bool) -> None:
    """
    Start advertising
    """


# extmod/modtrezorio/modtrezorio-ble.h
def stop_advertising(whitelist: bool) -> None:
    """
    Stop advertising
    """


# extmod/modtrezorio/modtrezorio-ble.h
def disconnect() -> None:
    """
    Disconnect BLE
    """
