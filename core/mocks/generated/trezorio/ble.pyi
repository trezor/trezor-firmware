from typing import *
INTERNAL: int # interface id for internal (stm<->nrf) connection
EXTERNAL: int # interface id for ble client connection


# extmod/modtrezorio/modtrezorio-ble.h
def update_init(data: bytes, binsize: int) -> bool:
    """
    Initializes the BLE firmware update. Returns true if the update finished
    with only the initial chunk. False means calling `update_chunk` is
    expected.
    """


# extmod/modtrezorio/modtrezorio-ble.h
def update_chunk(chunk: bytes) -> bool:
    """
    Writes next chunk of BLE firmware update. Returns true if the update is
    finished, or false if more chunks are expected.
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
