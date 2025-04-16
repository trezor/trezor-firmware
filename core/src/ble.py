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
