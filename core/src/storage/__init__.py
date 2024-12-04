# make sure to import cache unconditionally at top level so that it is imported (and retained) together with the storage module
from typing import TYPE_CHECKING

from storage import cache, common, device

if TYPE_CHECKING:
    from typing import Tuple

    pass


def wipe(clear_cache: bool = True) -> None:
    """
    Wipes the storage.
    If the device should communicate after wipe, use `clear_cache=False` and clear cache manually later using
    `wipe_cache()`.
    """
    from trezor import config

    config.wipe()
    if clear_cache:
        cache.clear_all()


def wipe_cache(excluded: Tuple[bytes, bytes] | None = None) -> None:
    cache.clear_all(excluded)


def init_unlocked() -> None:
    # Check for storage version upgrade.
    version = device.get_version()
    if version == common.STORAGE_VERSION_01:
        _migrate_from_version_01()

    # In FWs <= 2.3.1 'version' denoted whether the device is initialized or not.
    # In 2.3.2 we have introduced a new field 'initialized' for that.
    if device.is_version_stored() and not device.is_initialized():
        common.set_bool(common.APP_DEVICE, device.INITIALIZED, True, public=True)


def reset(excluded: Tuple[bytes, bytes] | None) -> None:
    """
    Wipes storage but keeps the device id unchanged.
    """
    device_id = device.get_device_id()
    wipe(clear_cache=False)
    wipe_cache(excluded)
    common.set(common.APP_DEVICE, device.DEVICE_ID, device_id.encode(), public=True)


def _migrate_from_version_01() -> None:
    # Make the U2F counter public and writable even when storage is locked.
    # U2F counter wasn't public, so we are intentionally not using storage.device module.
    counter = common.get(common.APP_DEVICE, device.U2F_COUNTER)
    if counter is not None:
        device.set_u2f_counter(int.from_bytes(counter, "big"))
        # Delete the old, non-public U2F_COUNTER.
        common.delete(common.APP_DEVICE, device.U2F_COUNTER)
    # set_current_version
    device.set_version(common.STORAGE_VERSION_CURRENT)
