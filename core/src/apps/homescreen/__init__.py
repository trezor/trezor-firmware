import storage
import storage.cache
import storage.device
from trezor import config, wire
from trezor.enums import MessageType
from trezor.ui.layouts.homescreen import Busyscreen, Homescreen, Lockscreen

from apps.base import busy_expiry_ms, lock_device
from apps.common.authorization import is_set_any_session


async def busyscreen() -> None:
    await Busyscreen(busy_expiry_ms())


async def homescreen() -> None:
    from trezor import utils

    if storage.device.is_initialized():
        label = storage.device.get_label()
    else:
        label = f"Trezor Model {utils.MODEL}"

    notification = None
    notification_is_error = False
    if is_set_any_session(MessageType.AuthorizeCoinJoin):
        # TODO: is too long for TR
        notification = "COINJOIN AUTHORIZED"
    elif storage.device.is_initialized() and storage.device.no_backup():
        notification = "SEEDLESS"
        notification_is_error = True
    elif storage.device.is_initialized() and storage.device.unfinished_backup():
        notification = "BACKUP FAILED"
        notification_is_error = True
    elif storage.device.is_initialized() and storage.device.needs_backup():
        notification = "BACKUP NEEDED"
    elif storage.device.is_initialized() and not config.has_pin():
        notification = "PIN NOT SET"
    elif storage.device.get_experimental_features():
        # TODO: is too long for TR
        notification = "EXPERIMENTAL MODE"

    await Homescreen(
        label=label,
        notification=notification,
        notification_is_error=notification_is_error,
        hold_to_lock=config.has_pin(),
    )
    lock_device()


async def lockscreen() -> None:
    from apps.common.request_pin import can_lock_device
    from apps.base import unlock_device

    # Only show the lockscreen UI if the device can in fact be locked.
    if can_lock_device():
        await Lockscreen(label=storage.device.get_label())
    # Otherwise proceed directly to unlock() call. If the device is already unlocked,
    # it should be a no-op storage-wise, but it resets the internal configuration
    # to an unlocked state.
    try:
        await unlock_device()
    except wire.PinCancelled:
        pass
