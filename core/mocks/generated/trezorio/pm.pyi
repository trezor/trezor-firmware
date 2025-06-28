from typing import *
# Status codes:
PM_OK: int
PM_NOT_INITIALIZED: int
PM_REQUEST_REJECTED: int
PM_ERROR: int
# Wakeup flags:
WAKEUP_FLAG_BUTTON: int
WAKEUP_FLAG_POWER: int
WAKEUP_FLAG_BLE: int
WAKEUP_FLAG_NFC: int
WAKEUP_FLAG_RTC: int


# upymod/modtrezorio/modtrezorio-pm.h
def suspend() -> tuple[int, int]:
    """
    Suspends the device. Returns tuple (status, wakeup_flags).
    Status codes: PM_OK=0, PM_NOT_INITIALIZED=1, PM_REQUEST_REJECTED=2,
    PM_ERROR=3
    Wakeup flags: BUTTON=1, POWER=2, BLE=4, NFC=8, RTC=16
    """
