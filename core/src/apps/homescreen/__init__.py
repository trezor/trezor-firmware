from typing import Coroutine

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
    from trezor import TR

    if storage.device.is_initialized():
        label = storage.device.get_label()
    else:
        label = None

    # TODO: add notification that translations are out of date

    notification = None
    notification_is_error = False
    if is_set_any_session(MessageType.AuthorizeCoinJoin):
        notification = TR.homescreen__title_coinjoin_authorized
    elif storage.device.is_initialized() and storage.device.no_backup():
        notification = TR.homescreen__title_seedless
        notification_is_error = True
    elif storage.device.is_initialized() and storage.device.unfinished_backup():
        notification = TR.homescreen__title_backup_failed
        notification_is_error = True
    elif storage.device.is_initialized() and storage.device.needs_backup():
        notification = TR.homescreen__title_backup_needed
    elif storage.device.is_initialized() and not config.has_pin():
        notification = TR.homescreen__title_pin_not_set
    elif storage.device.get_experimental_features():
        notification = TR.homescreen__title_experimental_mode

    await Homescreen(
        label=label,
        notification=notification,
        notification_is_error=notification_is_error,
        hold_to_lock=config.has_pin(),
    )
    lock_device()


async def _lockscreen(screensaver: bool = False) -> None:
    from apps.base import unlock_device
    from apps.common.request_pin import can_lock_device

    # Only show the lockscreen UI if the device can in fact be locked, or if it is
    # and OLED device (in which case the lockscreen is a screensaver).
    if can_lock_device() or screensaver:
        await Lockscreen(
            label=storage.device.get_label(),
            coinjoin_authorized=is_set_any_session(MessageType.AuthorizeCoinJoin),
        )
    # Otherwise proceed directly to unlock() call. If the device is already unlocked,
    # it should be a no-op storage-wise, but it resets the internal configuration
    # to an unlocked state.
    try:
        await unlock_device()
    except wire.PinCancelled:
        pass


def lockscreen() -> Coroutine[None, None, None]:
    return _lockscreen()


def screensaver() -> Coroutine[None, None, None]:
    return _lockscreen(screensaver=True)
