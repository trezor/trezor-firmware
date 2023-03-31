from typing import *
BLOCK_SIZE: int  # size of SD card block


# extmod/modtrezorio/modtrezorio-sdcard.h
def is_present() -> bool:
    """
    Returns True if SD card is detected, False otherwise.
    """


# extmod/modtrezorio/modtrezorio-sdcard.h
def power_on() -> None:
    """
    Power on the SD card interface.
    Raises OSError if the SD card cannot be powered on, e.g., when there
    is no SD card inserted.
    """


# extmod/modtrezorio/modtrezorio-sdcard.h
def power_off() -> None:
    """
    Power off the SD card interface.
    """


# extmod/modtrezorio/modtrezorio-sdcard.h
def capacity() -> int:
    """
    Returns capacity of the SD card in bytes, or zero if not present.
    """


# extmod/modtrezorio/modtrezorio-sdcard.h
def read(block_num: int, buf: bytearray) -> None:
    """
    Reads blocks starting with block_num from the SD card into buf.
    Number of bytes read is length of buf rounded down to multiply of
    SDCARD_BLOCK_SIZE. Returns True if in case of success, False otherwise.
    """


# extmod/modtrezorio/modtrezorio-sdcard.h
def write(block_num: int, buf: bytes) -> None:
    """
    Writes blocks starting with block_num from buf to the SD card.
    Number of bytes written is length of buf rounded down to multiply of
    SDCARD_BLOCK_SIZE. Returns True if in case of success, False otherwise.
    """
