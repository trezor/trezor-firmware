from storage import cache, common, device
from trezor import config


def set_current_version() -> None:
    device.set_version(common.STORAGE_VERSION_CURRENT)


def wipe() -> None:
    config.wipe()
    cache.clear_all()


def init_unlocked() -> None:
    # Check for storage version upgrade.
    version = device.get_version()
    if version == common.STORAGE_VERSION_01:
        _migrate_from_version_01()
    if version == common.STORAGE_VERSION_02:
        _migrate_from_version_02()


def reset() -> None:
    device_id = device.get_device_id()
    wipe()
    common.set(common.APP_DEVICE, device.DEVICE_ID, device_id.encode(), public=True)
    set_current_version()


def _migrate_from_version_01() -> None:
    # Make the U2F counter public and writable even when storage is locked.
    # U2F counter wasn't public, so we are intentionally not using storage.device module.
    counter = common.get(common.APP_DEVICE, device.U2F_COUNTER)
    if counter is not None:
        device.set_u2f_counter(int.from_bytes(counter, "big"))
        # Delete the old, non-public U2F_COUNTER.
        common.delete(common.APP_DEVICE, device.U2F_COUNTER)
    _migrate_from_version_02()


def _migrate_from_version_02() -> None:
    # <= 2.3.1 used storage version as a flag denoting initialization
    if device.is_initialized():
        raise RuntimeError  # So this should not happen.
    # Because the version is written it means the device is initialized.
    common.set_bool(common.APP_DEVICE, device.INITIALIZED, True, public=True)
    set_current_version()
