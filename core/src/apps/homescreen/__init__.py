from typing import Coroutine

import storage
import storage.device
import trezorui_api
from trezor import config, utils, wire
from trezor.enums import MessageType
from trezor.ui.layouts.homescreen import Busyscreen, Homescreen, Lockscreen

from apps.base import busy_expiry_ms
from apps.common.authorization import is_set_any_session
from apps.common.lock_manager import lock_device


async def busyscreen() -> None:
    obj = Busyscreen(busy_expiry_ms())
    try:
        await obj.get_result()
    finally:
        obj.__del__()


async def homescreen() -> None:
    from trezor import TR, loop

    if utils.USE_THP:
        # HOTFIX: allow some additional time for THP background tasks to
        # finish processing the last ACK before starting the creation and
        # painting of the homescreen (which may hog the CPU for >100ms).
        # For more details, see #6126.
        await loop.sleep(0)

    if storage.device.is_initialized():
        label = storage.device.get_label()
    else:
        label = None

    # TODO: add notification that translations are out of date

    notification = None
    notification_level = 1  # 0 = strong warning, 1 = warning, 2 = info, 3 = success
    if is_set_any_session(MessageType.AuthorizeCoinJoin):
        notification = TR.homescreen__title_coinjoin_authorized
        notification_level = 3
    elif storage.device.is_initialized() and storage.device.no_backup():
        notification = TR.homescreen__title_seedless
        notification_level = 0
    elif storage.device.is_initialized() and storage.device.unfinished_backup():
        notification = TR.homescreen__title_backup_failed
        notification_level = 0
    elif storage.device.is_initialized() and storage.device.needs_backup():
        notification = TR.homescreen__title_backup_needed
        notification_level = 1
    elif storage.device.is_initialized() and not config.has_pin():
        notification = TR.homescreen__title_pin_not_set
        notification_level = 1
    elif storage.device.get_experimental_features():
        notification = TR.homescreen__title_experimental_mode
        notification_level = 2

    obj = Homescreen(
        label=label,
        notification=notification,
        notification_level=notification_level,
        lockable=config.has_pin(),
    )
    try:
        res = await obj.get_result()
    finally:
        obj.__del__()

    if utils.INTERNAL_MODEL == "T3W1":
        if res is trezorui_api.INFO:
            from .device_menu import handle_device_menu

            return await handle_device_menu()
    lock_device()


async def _lockscreen(screensaver: bool = False) -> None:
    from apps.common.lock_manager import unlock_device
    from apps.common.request_pin import can_lock_device

    # Only show the lockscreen UI if the device can in fact be locked, or if it is
    # and OLED device (in which case the lockscreen is a screensaver).
    if can_lock_device() or screensaver:
        obj = Lockscreen(
            label=storage.device.get_label(),
            coinjoin_authorized=is_set_any_session(MessageType.AuthorizeCoinJoin),
        )
        try:
            await obj.get_result()
        finally:
            obj.__del__()
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
