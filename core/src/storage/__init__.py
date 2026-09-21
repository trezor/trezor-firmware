# make sure to import cache unconditionally at top level so that it is imported (and retained) together with the storage module
from typing import TYPE_CHECKING

from storage import cache, common, device

if TYPE_CHECKING:
    from buffer_types import AnyBytes


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


def wipe_cache(excluded: tuple[AnyBytes, AnyBytes] | None = None) -> None:
    cache.clear_all(excluded)


def reset(excluded: tuple[AnyBytes, AnyBytes] | None) -> None:
    """
    Wipes storage but keeps the device id, device secret, and credential counter unchanged.
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

