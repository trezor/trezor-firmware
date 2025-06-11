import storage.device
import trezorble as ble
import trezorui_api
from trezor import TR, config, log, utils
from trezor.ui.layouts import interact
from trezor.wire import ActionCancelled
from trezorui_api import DeviceMenuResult


async def _prompt_auto_lock_delay() -> int:
    auto_lock_delay_ms = await interact(
        trezorui_api.request_duration(
            title=TR.auto_lock__title,
            duration_ms=storage.device.get_autolock_delay_ms(),
            min_ms=storage.device.AUTOLOCK_DELAY_MINIMUM,
            max_ms=storage.device.AUTOLOCK_DELAY_MAXIMUM,
            description=TR.auto_lock__description,
        ),
        br_name=None,
    )

    if auto_lock_delay_ms is not trezorui_api.CANCELLED:
        assert isinstance(auto_lock_delay_ms, int)
        assert auto_lock_delay_ms >= storage.device.AUTOLOCK_DELAY_MINIMUM
        assert auto_lock_delay_ms <= storage.device.AUTOLOCK_DELAY_MAXIMUM
        return auto_lock_delay_ms
    else:
        raise ActionCancelled  # user cancelled request number prompt


async def handle_device_menu() -> None:
    from trezor import strings

    # TODO: unify with notification handling in `apps/homescreen/__init__.py:homescreen()`
    failed_backup = (
        storage.device.is_initialized() and storage.device.unfinished_backup()
    )
    # MOCK DATA
    paired_devices = ["Trezor Suite"] if ble.is_connected() else []
    # ###
    firmware_version = ".".join(map(str, utils.VERSION))
    device_name = storage.device.get_label() or "Trezor"

    auto_lock_ms = storage.device.get_autolock_delay_ms()
    auto_lock_delay = strings.format_autolock_duration(auto_lock_ms)

    log.debug(
        __name__,
        f"device menu, BLE state: {ble.connection_flags()} (peers: {ble.peer_count()})",
    )

    menu_result = await interact(
        trezorui_api.show_device_menu(
            failed_backup=failed_backup,
            paired_devices=paired_devices,
            firmware_version=firmware_version,
            device_name=device_name,
            auto_lock_delay=auto_lock_delay,
        ),
        "device_menu",
    )

    if menu_result is DeviceMenuResult.DevicePair:
        from apps.management.ble.pair_new_device import pair_new_device

        await pair_new_device()
    elif menu_result is DeviceMenuResult.ScreenBrightness:
        from trezor.ui.layouts import set_brightness

        await set_brightness()
    elif menu_result is DeviceMenuResult.WipeDevice:
        from trezor.messages import WipeDevice

        from apps.management.wipe_device import wipe_device

        await wipe_device(WipeDevice())
    elif menu_result is DeviceMenuResult.AutoLockDelay:

        if config.has_pin():

            auto_lock_delay_ms = await _prompt_auto_lock_delay()
            storage.device.set_autolock_delay_ms(auto_lock_delay_ms)
    elif isinstance(menu_result, tuple):
        # It's a tuple with (result_type, index)
        result_type, index = menu_result
        if result_type is DeviceMenuResult.DeviceDisconnect:
            from trezor.messages import BleUnpair

            from apps.management.ble.unpair import unpair

            await unpair(BleUnpair(all=False))  # FIXME we can only unpair current
        else:
            raise RuntimeError(f"Unknown menu {result_type}, {index}")
    else:
        raise RuntimeError(f"Unknown menu {menu_result}")
