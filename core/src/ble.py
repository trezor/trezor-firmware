# BLE setup - called from main.py near the end of firmware startup
# please note BLE may already be set up by bootloader

import utime

import storage.device
import trezorble as ble
from trezor import log, utils

try:
    ble.start_comm()

    start_ms = utime.ticks_ms()

    while utime.ticks_diff(utime.ticks_ms(), start_ms) < 5000:
        if utils.EMULATOR or ble.is_started():
            break

    # allow connections from bonded peers if any
    if ble.peer_count() > 0:
        ble.start_advertising(True, storage.device.get_label())
except Exception as e:
    log.exception(__name__, e)
