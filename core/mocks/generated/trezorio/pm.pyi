from typing import *
# Wakeup flags:
WAKEUP_FLAG_BUTTON: int
WAKEUP_FLAG_POWER: int
WAKEUP_FLAG_BLE: int
WAKEUP_FLAG_NFC: int
WAKEUP_FLAG_RTC: int


# upymod/modtrezorio/modtrezorio-pm.h
def suspend() -> int:
    """
    Suspends the device. Returns wakeup flag. Raises RuntimeError on
    failure.
    Wakeup flags: BUTTON=1, POWER=2, BLE=4, NFC=8, RTC=16
    """


# upymod/modtrezorio/modtrezorio-pm.h
def is_usb_connected() -> bool:
    """
    Returns True if USB is connected, False otherwise. Raises RuntimeError
    on failure.
    """
