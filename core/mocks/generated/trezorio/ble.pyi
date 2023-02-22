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
def write(self, msg: bytes) -> int:
    """
    Sends message using BLE.
    """
