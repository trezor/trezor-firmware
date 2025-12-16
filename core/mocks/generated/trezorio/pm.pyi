from typing import *
from buffer_types import *
# Wakeup flags:
WAKEUP_FLAG_BUTTON: int
WAKEUP_FLAG_POWER: int
WAKEUP_FLAG_BLE: int
WAKEUP_FLAG_NFC: int
WAKEUP_FLAG_RTC: int
WAKEUP_FLAG_USB: int

# Power manager event flags:
EVENT_POWER_STATUS_CHANGED: int
EVENT_CHARGING_STATUS_CHANGED: int
EVENT_USB_CONNECTED_CHANGED: int
EVENT_WIRELESS_CONNECTED_CHANGED: int
EVENT_NTC_CONNECTED_CHANGED: int
EVENT_CHARGING_LIMITED_CHANGED: int
EVENT_BATTERY_OCV_JUMP_DETECTED: int
EVENT_BATTERY_TEMP_JUMP_DETECTED: int
EVENT_SOC_UPDATED: int


# upymod/modtrezorio/modtrezorio-pm.h
def soc() -> int:
   """
   Returns the state of charge (SoC) in percent (0-100). Raises RuntimeError
   on failure.
   """


# upymod/modtrezorio/modtrezorio-pm.h
def suspend() -> int:
    """
    Suspends the device. Returns wakeup flag. Raises RuntimeError on
    failure.
    Wakeup flags: BUTTON=1, POWER=2, BLE=4, NFC=8, RTC=16
    """


# upymod/modtrezorio/modtrezorio-pm.h
def hibernate() -> None:
    """
    Hibernates the device. Raises RuntimeError on failure.
    """


# upymod/modtrezorio/modtrezorio-pm.h
def is_usb_connected() -> bool:
    """
    Returns True if USB is connected, False otherwise. Raises RuntimeError
    on failure.
    """


# upymod/modtrezorio/modtrezorio-pm.h
def is_wireless_connected() -> bool:
    """
    Returns True if Wireless power source is connected, False otherwise.
    Raises RuntimeError on failure.
    """
