from typing import *


# extmod/modtrezorio/modtrezorio-ble.h
def update_init(data: bytes, binsize: int) -> int:
    """
    Initializes the BLE firmware update
    """


# extmod/modtrezorio/modtrezorio-ble.h
def update_chunk(chunk: bytes) -> int:
    """
    Writes next chunk of BLE firmware update
    """


# extmod/modtrezorio/modtrezorio-ble.h
def write_int(self, msg: bytes) -> int:
    """
    Sends internal message to NRF.
    """


# extmod/modtrezorio/modtrezorio-ble.h
def write_ext(self, msg: bytes) -> int:
    """
    Sends message over BLE
    """


# extmod/modtrezorio/modtrezorio-ble.h
def erase_bonds() -> None:
    """
    Erases all BLE bonds
    """


# extmod/modtrezorio/modtrezorio-ble.h
def disconnect() -> None:
    """
    Disconnect BLE
    """
