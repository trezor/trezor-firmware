from typing import TYPE_CHECKING

import storage.device as storage_device
from storage.cache_common import APP_COMMON_BUSY_DEADLINE_MS
from trezor import config, utils, wire, workflow
from trezor.wire import context
from trezor.wire.message_handler import filters, remove_filter

if utils.USE_POWER_MANAGER:
    from trezor import io
    from trezor.power_management.autodim import autodim_display
    from trezor.power_management.suspend import suspend_device

if TYPE_CHECKING:
    from trezor import protobuf
    from trezor.wire import Handler, Msg

_SCREENSAVER_IS_ON = False


if not utils.USE_POWER_MANAGER:

    def notify_suspend() -> None:
        pass

else:
    from trezor import loop

    _SHOULD_SUSPEND = False
    _notify_power_button: loop.mailbox[None] = loop.mailbox()

    def _prepare_suspend() -> None:
        """Signal that the device should be suspended by the default task.

        Sets a suspend homescreen for next time the default task is invoked."""
        if not utils.EMULATOR:
            # FIXME: suspend not implemented on emulator
            _SHOULD_SUSPEND = True
            set_homescreen()

    def notify_suspend() -> None:
        """Signal that the the device should be suspended in the next cycle.

        Notifies an asynchronous task to perform the suspend in a separate thread.
        """
        _notify_power_button.put(None)

    async def _power_handler() -> None:
        """Handler for the notify_suspend signal."""
        while True:
            await _notify_power_button
            lock_device_if_unlocked()

    async def _suspend_and_resume() -> None:
        """Default task that suspends the device and invokes resumption.

        Must be async (or more precisely a generator) so that we can schedule it
        via set_default."""
        from trezor.ui import CURRENT_LAYOUT

        wakeup_flag = suspend_device()

        if wakeup_flag == io.pm.WAKEUP_FLAG_BUTTON:
            if CURRENT_LAYOUT is not None:
                CURRENT_LAYOUT.layout.request_complete_repaint()

        _SHOULD_SUSPEND = False
        set_homescreen()

    def lock_device_if_unlocked_on_battery() -> None:
        """Lock the device if it is unlocked and running on battery or wireless charger."""
        if not io.pm.is_usb_connected():
            lock_device_if_unlocked()


def set_homescreen() -> None:
    import storage.recovery as storage_recovery

    from apps.common import backup

    set_default = workflow.set_default  # local_cache_attribute

    if utils.USE_POWER_MANAGER and _SHOULD_SUSPEND:
        set_default(_suspend_and_resume)

    elif context.cache_is_set(APP_COMMON_BUSY_DEADLINE_MS):
        from apps.homescreen import busyscreen

        set_default(busyscreen)

    elif not config.is_unlocked():
        from apps.homescreen import lockscreen

        set_default(lockscreen)

    elif _SCREENSAVER_IS_ON:
        from apps.homescreen import screensaver

        set_default(screensaver, restart=True)

    elif storage_recovery.is_in_progress() or backup.repeated_backup_enabled():
        from apps.management.recovery_device.homescreen import recovery_homescreen

        set_default(recovery_homescreen)

    else:
        from apps.homescreen import homescreen

        set_default(homescreen)


def lock_device(interrupt_workflow: bool = True) -> None:
    if config.has_pin():
        config.lock()
        filters.append(_pinlock_filter)
        set_homescreen()
        if interrupt_workflow:
            workflow.close_others()
        # TODO: should we suspend the device here?


def lock_device_if_unlocked() -> None:
    from apps.common.request_pin import can_lock_device

    if not utils.USE_BACKLIGHT and not can_lock_device():
        # on OLED devices without PIN, trigger screensaver
        global _SCREENSAVER_IS_ON

        _SCREENSAVER_IS_ON = True
        set_homescreen()

    elif config.is_unlocked():
        lock_device(interrupt_workflow=workflow.autolock_interrupts_workflow)

    if utils.USE_POWER_MANAGER:
        _prepare_suspend()


async def unlock_device() -> None:
    """Ensure the device is in unlocked state.

    If the storage is locked, attempt to unlock it. Reset the homescreen and the wire
    handler.
    """
    from apps.common.request_pin import verify_user_pin

    global _SCREENSAVER_IS_ON

    if not config.is_unlocked():
        # verify_user_pin will raise if the PIN was invalid
        await verify_user_pin()

    _SCREENSAVER_IS_ON = False
    set_homescreen()
    remove_filter(_pinlock_filter)


def _pinlock_filter(msg_type: int, prev_handler: Handler[Msg]) -> Handler[Msg]:
    if msg_type in workflow.ALLOW_WHILE_LOCKED:
        return prev_handler

    async def wrapper(msg: Msg) -> protobuf.MessageType:
        await unlock_device()
        return await prev_handler(msg)

    return wrapper


# this function is also called when handling ApplySettings
def reload_settings_from_storage() -> None:
    from trezor import ui

    workflow.idle_timer.set(
        storage_device.get_autolock_delay_ms(), lock_device_if_unlocked
    )

    if utils.USE_POWER_MANAGER:
        # autodim setting is not from storage but keeping it here for simplicity
        workflow.idle_timer.set(30_000, autodim_display)
        workflow.idle_timer.set(
            storage_device.get_autolock_delay_battery_ms(),
            lock_device_if_unlocked_on_battery,
        )
    wire.message_handler.EXPERIMENTAL_ENABLED = (
        storage_device.get_experimental_features()
    )
    if ui.display.orientation() != storage_device.get_rotation():
        ui.backlight_fade(ui.BacklightLevels.DIM)
        ui.display.orientation(storage_device.get_rotation())


def boot() -> None:
    set_homescreen()
    if utils.USE_POWER_MANAGER:
        loop.schedule(_power_handler())
