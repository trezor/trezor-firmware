from trezor import config

from apps.common import cache
from apps.common.storage import common, device, slip39


def set_current_version():
    device.set_version(common._STORAGE_VERSION_CURRENT)


def is_initialized() -> bool:
    return device.is_version_stored() and not slip39.is_in_progress()


def wipe():
    config.wipe()
    cache.clear()


def init_unlocked():
    # Check for storage version upgrade.
    version = device.get_version()
    if version == common._STORAGE_VERSION_01:
        _migrate_from_version_01()


def _migrate_from_version_01():
    # Make the U2F counter public and writable even when storage is locked.
    # U2F counter wasn't public, so we are intentionally not using storage.device module.
    counter = common._get(common._APP_DEVICE, device._U2F_COUNTER)
    if counter is not None:
        device.set_u2f_counter(int.from_bytes(counter, "big"))
        # Delete the old, non-public U2F_COUNTER.
        common._delete(common._APP_DEVICE, device._U2F_COUNTER)
    set_current_version()
