import storage.device as storage_device
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
            duration_ms=storage_device.get_autolock_delay_ms(),
            min_ms=storage_device.AUTOLOCK_DELAY_MINIMUM,
            max_ms=storage_device.AUTOLOCK_DELAY_MAXIMUM,
            description=TR.auto_lock__description,
        ),
        br_name=None,
    )

    if auto_lock_delay_ms is not trezorui_api.CANCELLED:
        assert isinstance(auto_lock_delay_ms, int)
        assert auto_lock_delay_ms >= storage_device.AUTOLOCK_DELAY_MINIMUM
        assert auto_lock_delay_ms <= storage_device.AUTOLOCK_DELAY_MAXIMUM
        return auto_lock_delay_ms
    else:
        raise ActionCancelled  # user cancelled request number prompt


async def handle_device_menu() -> None:
    from trezor import strings

    # TODO: unify with notification handling in `apps/homescreen/__init__.py:homescreen()`
    failed_backup = (
        storage_device.is_initialized() and storage_device.unfinished_backup()
    )
    # MOCK DATA
    paired_devices = ["Trezor Suite"] if ble.is_connected() else []
    # ###
    firmware_version = ".".join(map(str, utils.VERSION))
    device_name = (
        (storage_device.get_label() or "Trezor")
        if storage_device.is_initialized()
        else None
    )

    auto_lock_ms = storage_device.get_autolock_delay_ms()
    auto_lock_delay = strings.format_autolock_duration(auto_lock_ms)

    if __debug__:
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
            led=(
                storage_device.get_rgb_led()
                if (storage_device.is_initialized() and utils.USE_RGB_LED)
                else None
            ),
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
            storage_device.set_autolock_delay_ms(auto_lock_delay_ms)
    elif menu_result is DeviceMenuResult.DeviceName:
        from trezor.messages import ApplySettings

        from apps.management.apply_settings import apply_settings

        assert storage_device.is_initialized()
        label = await interact(
            trezorui_api.request_string(
                prompt=TR.device_name__enter,
                max_len=storage_device.LABEL_MAXLENGTH,
                allow_empty=False,
                prefill=storage_device.get_label(),
            ),
            "device_name",
        )
        assert isinstance(label, str)
        await apply_settings(ApplySettings(label=label))
    elif menu_result is DeviceMenuResult.Led:
        from trezor import io
        from trezor.ui.layouts import confirm_action

        enable = not storage_device.get_rgb_led()
        await confirm_action(
            "led__settings",
            TR.led__title,
            TR.led__enable if enable else TR.led__disable,
        )

        io.rgb_led.rgb_led_set_enabled(enable)
        storage_device.set_rgb_led(enable)
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
