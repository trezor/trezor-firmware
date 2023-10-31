from typing import *


# extmod/modtrezorutils/modtrezorutils-meminfo.h
def meminfo(filename: str) -> None:
    """Dumps map of micropython GC arena to a file.
    The JSON file can be decoded by analyze.py
    Only available in the emulator.
     """


# extmod/modtrezorutils/modtrezorutils.c
def consteq(sec: bytes, pub: bytes) -> bool:
    """
    Compares the private information in `sec` with public, user-provided
    information in `pub`.  Runs in constant time, corresponding to a length
    of `pub`.  Can access memory behind valid length of `sec`, caller is
    expected to avoid any invalid memory access.
    """


# extmod/modtrezorutils/modtrezorutils.c
def memcpy(
    dst: bytearray | memoryview,
    dst_ofs: int,
    src: bytes,
    src_ofs: int,
    n: int | None = None,
) -> int:
    """
    Copies at most `n` bytes from `src` at offset `src_ofs` to
    `dst` at offset `dst_ofs`. Returns the number of actually
    copied bytes. If `n` is not specified, tries to copy
    as much as possible.
    """


# extmod/modtrezorutils/modtrezorutils.c
def halt(msg: str | None = None) -> None:
    """
    Halts execution.
    """


# extmod/modtrezorutils/modtrezorutils.c
def firmware_hash(
    challenge: bytes | None = None,
    callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """
    Computes the Blake2s hash of the firmware with an optional challenge as
    the key.
    """


# extmod/modtrezorutils/modtrezorutils.c
def firmware_vendor() -> str:
    """
    Returns the firmware vendor string from the vendor header.
    """


# extmod/modtrezorutils/modtrezorutils.c
def unit_color() -> int | None:
    """
    Returns the color of the unit.
    """


# extmod/modtrezorutils/modtrezorutils.c
def unit_btconly() -> bool | None:
    """
    Returns True if the unit is BTConly.
    """


# extmod/modtrezorutils/modtrezorutils.c
def reboot_to_bootloader(
    boot_command : int = 0,
    boot_args : bytes | None = None,
) -> None:
    """
    Reboots to bootloader.
    """


# extmod/modtrezorutils/modtrezorutils.c
def check_firmware_header(
    header : bytes
) -> dict:
    """
    Checks firmware image and vendor header and returns
       { "version": (major, minor, patch),
         "vendor": string,
         "fingerprint": bytes,
         "hash": bytes
       }
    """


# extmod/modtrezorutils/modtrezorutils.c
def bootloader_locked() -> bool | None:
    """
    Returns True/False if the the bootloader is locked/unlocked and None if
    the feature is not supported.
    """
SCM_REVISION: bytes
"""Git commit hash of the firmware."""
VERSION_MAJOR: int
"""Major version."""
VERSION_MINOR: int
"""Minor version."""
VERSION_PATCH: int
"""Patch version."""
USE_SD_CARD: bool
"""Whether the hardware supports SD card."""
USE_BACKLIGHT: bool
"""Whether the hardware supports backlight brightness control."""
USE_OPTIGA: bool
"""Whether the hardware supports Optiga secure element."""
MODEL: str
"""Model name."""
MODEL_FULL_NAME: str
"""Full name including Trezor prefix."""
INTERNAL_MODEL: str
"""Internal model code."""
EMULATOR: bool
"""Whether the firmware is running in the emulator."""
BITCOIN_ONLY: bool
"""Whether the firmware is Bitcoin-only."""
UI_LAYOUT: str
"""UI layout identifier ("tt" for model T, "tr" for models One and R)."""
