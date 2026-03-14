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
    Returns the state of charge (SoC) in percent (0-100). Raises
    RuntimeError on failure.
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


# upymod/modtrezorio/modtrezorio-pm.h
def set_emu_battery_state(
    soc: int | None = None,
    usb_connected: bool | None = None,
    wireless_connected: bool | None = None,
    ntc_connected: bool | None = None,
    charging_limited: bool | None = None,
    temp_control_active: bool | None = None,
    battery_connected: bool | None = None,
    charging_status: int | None = None,
    power_status: int | None = None,
) -> None:
    """
    Set emulated battery/power state with fine-grained control.
    Only available on emulator. Pass None to leave a field unchanged.
    charging_status: 0=idle, 1=discharging, 2=charging (auto-derived from
      connections if not set)
    power_status: 0=hibernate, 1=charging, 2=suspend, 3=shutting_down,
      4=power_save, 5=active
    """
