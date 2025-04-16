# BLE setup - called from main.py near the end of firmware startup
# please note BLE may already be set up by bootloader

import storage.device
import trezorble as ble
from trezor import log

try:
    ble.start_comm()

    # allow connections from bonded peers if any
    if ble.peer_count() > 0:
        ble.start_advertising(True, storage.device.get_label())
except Exception as e:
    log.exception(__name__, e)
