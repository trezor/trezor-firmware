from micropython import const

from storage import cache, common, device_old
from trezor import config

import trezorstoragedevice as device
import trezorstoragerecovery as recovery  # noqa F401
import trezorstorageresidentcredentials as resident_credentials  # noqa F401

STORAGE_VERSION_01 = b"\x01"
STORAGE_VERSION_CURRENT = b"\x02"

MAX_RESIDENT_CREDENTIALS = const(100)


def set_current_version() -> None:
    device.set_version(STORAGE_VERSION_CURRENT)


def wipe() -> None:
    config.wipe()
    cache.clear_all()


def init_unlocked() -> None:
    # Check for storage version upgrade.
    version = device.get_version()
    if version == STORAGE_VERSION_01:
        _migrate_from_version_01()

    # In FWs <= 2.3.1 'version' denoted whether the device is initialized or not.
    # In 2.3.2 we have introduced a new field 'initialized' for that.
    if device.is_version_stored() and not device.is_initialized():
        device.set_is_initialized(True)


def reset() -> None:
    """
    Wipes storage but keeps the device id unchanged.
    """
    device_id = device.get_device_id()
    wipe()
    device.set_device_id(device_id)


def _migrate_from_version_01() -> None:
    # Make the U2F counter public and writable even when storage is locked.
    # U2F counter wasn't public, so we are intentionally not using storage.device module.
    counter = common.get(common.APP_DEVICE, device_old.U2F_COUNTER)
    if counter is not None:
        device.set_u2f_counter(int.from_bytes(counter, "big"))
        # Delete the old, non-public U2F_COUNTER.
        common.delete(common.APP_DEVICE, device_old.U2F_COUNTER)
    set_current_version()
