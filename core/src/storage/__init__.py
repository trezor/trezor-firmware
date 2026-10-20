# make sure to import cache unconditionally at top level so that it is imported (and retained) together with the storage module
from typing import TYPE_CHECKING

from storage import cache, common, device
from trezor import config

if TYPE_CHECKING:
    from buffer_types import AnyBytes


def wipe(clear_cache: bool = True) -> None:
    """
    Wipes the storage.
    If the device should communicate after wipe, use `clear_cache=False` and clear cache manually later using
    `wipe_cache()`.
    """
    config.wipe()
    if clear_cache:
        cache.clear_all()


def wipe_cache(excluded: tuple[AnyBytes, AnyBytes] | None = None) -> None:
    cache.clear_all(excluded)


def init_unlocked() -> None:
    # Check for storage version upgrade.
    version = device.get_version()
    if version == common.STORAGE_VERSION_01:
        _migrate_from_version_01()
    elif version == common.STORAGE_VERSION_02:
        _migrate_from_version_02()

    # In FWs <= 2.3.1 'version' denoted whether the device is initialized or not.
    # In 2.3.2 we have introduced a new field 'initialized' for that.
    if device.is_version_stored() and not device.is_initialized():
        common.set_bool(common.APP_DEVICE, device.INITIALIZED, True, public=True)


def reset(excluded: tuple[AnyBytes, AnyBytes] | None) -> None:
    """
    Wipes storage but keeps the device id. On THP builds it also keeps the device secret,
    the credential counter and the paired names, so existing pairings survive.
    """
    from trezor import utils

    device_id = device.get_device_id()
    if utils.USE_THP:
        device_secret = device.get_device_secret()
        credential_counter = device.get_cred_auth_key_counter()
        # keep the name cache since we're keeping BLE bonds as well as THP credentials
        paired_names = device.get_thp_paired_names()
    wipe(clear_cache=False)
    wipe_cache(excluded)
    common.set(common.APP_DEVICE, device.DEVICE_ID, device_id.encode(), public=True)
    if utils.USE_THP:
        common.set(common.APP_DEVICE, device.DEVICE_SECRET, device_secret)
        common.set(
            common.APP_DEVICE,
            device.CRED_AUTH_KEY_COUNTER,
            credential_counter,
        )
        if paired_names:
            common.set(common.APP_DEVICE, device.THP_PAIRED_NAMES, paired_names)


def lock() -> None:
    """Lock the storage. Encrypts the cache first, so the two stay in sync."""
    if not config.is_unlocked():
        # Load-bearing, not an optimization: `LockDevice` on an already locked device would
        # have `encrypt_cache` try to store a new device secret, and crash.
        return
    cache.encrypt_cache()
    config.lock()


def unlock(pin: str, salt: AnyBytes | None) -> bool:
    """Unlock the storage and decrypt the cache. False if the PIN was wrong."""
    was_locked = not config.is_unlocked()
    if not config.unlock(pin, salt):
        return False
    # debug-only: catches a lock path that skipped encryption
    assert not was_locked or cache.no_unexpected_plaintext()
    cache.decrypt_cache()
    return True


def _migrate_from_version_01() -> None:
    # Make the U2F counter public and writable even when storage is locked.
    # U2F counter wasn't public, so we are intentionally not using storage.device module.
    counter = common.get(common.APP_DEVICE, device.U2F_COUNTER)
    if counter is not None:
        device.set_u2f_counter(int.from_bytes(counter, "big"))
        # Delete the old, non-public U2F_COUNTER.
        common.delete(common.APP_DEVICE, device.U2F_COUNTER)
    # the device is now at version 2
    device.set_version(common.STORAGE_VERSION_02)

    # update from version 2 to version 3
    _migrate_from_version_02()


def _migrate_from_version_02() -> None:
    from trezor import utils

    # This update concerns Cardano derivation. There is no need for update for Bitcoin-only builds
    if not utils.BITCOIN_ONLY:
        from storage.device import get_backup_type, store_binary_mnemonic
        from trezor.enums import BackupType

        if get_backup_type() == BackupType.Bip39:
            # Ensure binary mnemonic is stored
            secret = device.get_mnemonic_secret()
            if secret is not None:
                store_binary_mnemonic(secret)

    # set_current_version
    device.set_version(common.STORAGE_VERSION_CURRENT)
