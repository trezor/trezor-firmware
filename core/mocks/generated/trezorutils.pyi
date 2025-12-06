from typing import *
from buffer_types import *


# upymod/modtrezorutils/modtrezorutils-meminfo.h
def meminfo(filename: str | None) -> None:
    """Dumps map of micropython GC arena to a file.
    The JSON file can be decoded by analyze-memory-dump.py
     """
from trezor import utils


# upymod/modtrezorutils/modtrezorutils.c
def consteq(sec: AnyBytes, pub: AnyBytes) -> bool:
    """
    Compares the private information in `sec` with public, user-provided
    information in `pub`.  Runs in constant time, corresponding to a length
    of `pub`.  Can access memory behind valid length of `sec`, caller is
    expected to avoid any invalid memory access.
    """


# upymod/modtrezorutils/modtrezorutils.c
def memcpy(
    dst: AnyBuffer,
    dst_ofs: int,
    src: AnyBytes,
    src_ofs: int,
    n: int | None = None,
) -> int:
    """
    Copies at most `n` bytes from `src` at offset `src_ofs` to
    `dst` at offset `dst_ofs`. Returns the number of actually
    copied bytes. If `n` is not specified, tries to copy
    as much as possible.
    """


# upymod/modtrezorutils/modtrezorutils.c
def memzero(
    dst: AnyBuffer,
) -> None:
    """
    Zeroes all bytes at `dst`.
    """


# upymod/modtrezorutils/modtrezorutils.c
def halt(msg: str | None = None) -> None:
    """
    Halts execution.
    """


# upymod/modtrezorutils/modtrezorutils.c
def firmware_hash(
    challenge: AnyBytes | None = None,
    callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """
    Computes the Blake2s hash of the firmware with an optional challenge as
    the key.
    """


# upymod/modtrezorutils/modtrezorutils.c
def firmware_vendor() -> str:
    """
    Returns the firmware vendor string from the vendor header.
    """


# upymod/modtrezorutils/modtrezorutils.c
def delegated_identity(index: int) -> bytes:
    """
    Returns the delegated identity key used for registration and space
    management at Quota Manager.
    """


# upymod/modtrezorutils/modtrezorutils.c
def unit_color() -> int | None:
    """
    Returns the color of the unit.
    """


# upymod/modtrezorutils/modtrezorutils.c
def unit_btconly() -> bool | None:
    """
    Returns True if the unit is BTConly.
    """


# upymod/modtrezorutils/modtrezorutils.c
def unit_packaging() -> int | None:
    """
    Returns the packaging version of the unit.
    """
if utils.USE_SERIAL_NUMBER:
    def serial_number() -> str:
        """
        Returns unit serial number.
        """


# upymod/modtrezorutils/modtrezorutils.c
def sd_hotswap_enabled() -> bool:
    """
    Returns True if SD card hot swapping is enabled
    """


# upymod/modtrezorutils/modtrezorutils.c
def presize_module(mod: module, n: int):
    """
    Ensure the module's dict is preallocated to an expected size.

    This is used in modules like `trezor`, whose dict size depends not only
    on the symbols defined in the file itself, but also on the number of
    submodules that will be inserted into the module's namespace.
    """


# upymod/modtrezorutils/modtrezorutils.c
def zero_unused_stack() -> None:
    """
    Zero unused stack memory.
    """


# upymod/modtrezorutils/modtrezorutils.c
def estimate_unused_stack() -> int:
    """
    Estimate unused stack size.
    """
if __debug__:
    def enable_oom_dump() -> None:
        """
        Dump GC info in case of an OOM.
        """
if __debug__:
    def clear_gc_info() -> None:
        """
        Clear GC heap stats.
        """
if __debug__:
    def get_gc_info() -> dict[str, int]:
        """
        Get GC heap stats, updated by `update_gc_info`.
        """
if __debug__:
    def update_gc_info() -> None:
        """
        Update current GC heap statistics.
        On emulator, also assert that free heap memory doesn't decrease.
        Enabled only for frozen debug builds.
        """
if __debug__:
    def check_heap_fragmentation() -> None:
        """
        Assert known sources for heap fragmentation.
        Enabled only for frozen debug builds.
        """


# upymod/modtrezorutils/modtrezorutils.c
def reboot_and_upgrade(
    hash : AnyBytes,
) -> None:
    """
    Reboots to perform upgrade to FW with specified hash.
    """


# upymod/modtrezorutils/modtrezorutils.c
def reboot_to_bootloader() -> None:
    """
    Reboots the device and stay in bootloader.
    """


# upymod/modtrezorutils/modtrezorutils.c
def reboot() -> None:
    """
    Reboots the device.
    """
VersionTuple = Tuple[int, int, int, int]


# upymod/modtrezorutils/modtrezorutils.c
class FirmwareHeaderInfo(NamedTuple):
    version: VersionTuple
    vendor: str
    fingerprint: AnyBytes
    hash: AnyBytes


# upymod/modtrezorutils/modtrezorutils.c
def check_firmware_header(header : AnyBytes) -> FirmwareHeaderInfo:
    """Parses incoming firmware header and returns information about it."""


# upymod/modtrezorutils/modtrezorutils.c
def bootloader_locked() -> bool | None:
    """
    Returns True/False if the bootloader is locked/unlocked and None if
    the feature is not supported.
    """


# upymod/modtrezorutils/modtrezorutils.c
def notify_send(event: int) -> None:
    """
    Sends a notification to host
    """


# upymod/modtrezorutils/modtrezorutils.c
def nrf_get_version() -> VersionTuple:
    """
    Reads version of nRF firmware
    """
SCM_REVISION: bytes
"""Git commit hash of the firmware."""
VERSION: VersionTuple
"""Firmware version as a tuple (major, minor, patch, build)."""
USE_BLE: bool
"""Whether the hardware supports BLE."""
USE_SD_CARD: bool
"""Whether the hardware supports SD card."""
USE_SERIAL_NUMBER: bool
"""Whether the hardware support exporting its serial number."""
USE_BACKLIGHT: bool
"""Whether the hardware supports backlight brightness control."""
USE_HAPTIC: bool
"""Whether the hardware supports haptic feedback."""
USE_RGB_LED: bool
"""Whether the hardware supports RGB LED."""
USE_OPTIGA: bool
"""Whether the hardware supports Optiga secure element."""
USE_TROPIC: bool
"""Whether the hardware supports Tropic Square secure element."""
USE_TOUCH: bool
"""Whether the hardware supports touch screen."""
USE_BUTTON: bool
"""Whether the hardware supports two-button input."""
USE_POWER_MANAGER: bool
"""Whether the hardware has a battery."""
USE_NRF: bool
"""Whether the hardware has a nRF chip."""
MODEL: str
"""Model name."""
MODEL_FULL_NAME: str
"""Full name including Trezor prefix."""
MODEL_USB_MANUFACTURER: str
"""USB Manufacturer name."""
MODEL_USB_PRODUCT: str
"""USB Product name."""
INTERNAL_MODEL: str
"""Internal model code."""
HOMESCREEN_MAXSIZE: int
"""Maximum size of user-uploaded homescreen in bytes."""
EMULATOR: bool
"""Whether the firmware is running in the emulator."""
BITCOIN_ONLY: bool
"""Whether the firmware is Bitcoin-only."""
UI_LAYOUT: str
"""UI layout identifier ("BOLT"-T, "CAESAR"-TS3, "DELIZIA"-TS5)."""
USE_THP: bool
"""Whether the firmware supports Trezor-Host Protocol (version 2)."""
NOTIFY_BOOT: int
"""Notification event: boot completed."""
NOTIFY_UNLOCK: int
"""Notification event: device unlocked from hardlock"""
NOTIFY_LOCK: int
"""Notification event: device locked to hardlock"""
NOTIFY_DISCONNECT: int
"""Notification event: user-initiated disconnect from host"""
NOTIFY_SETTING_CHANGE: int
"""Notification event: change of settings"""
NOTIFY_SOFTLOCK: int
"""Notification event: device soft-locked"""
NOTIFY_SOFTUNLOCK: int
"""Notification event: device soft-unlocked"""
NOTIFY_PIN_CHANGE: int
"""Notification event: PIN changed on the device"""
NOTIFY_WIPE: int
"""Notification event: factory reset (wipe) invoked"""
NOTIFY_UNPAIR: int
"""Notification event: BLE bonding for current connection deleted"""

if __debug__:
    DISABLE_ANIMATION: bool
    """Whether the firmware should disable animations."""
    LOG_STACK_USAGE: bool
    """Whether the firmware should log estimated stack usage."""
