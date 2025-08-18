import storage.device as storage_device
import trezorble as ble
import trezorui_api
from trezor import TR, config, log, utils
from trezor.ui.layouts import interact
from trezorui_api import DeviceMenuResult


async def handle_device_menu() -> None:
    from trezor import strings

    # TODO: unify with notification handling in `apps/homescreen/__init__.py:homescreen()`
    failed_backup = (
        storage_device.is_initialized() and storage_device.unfinished_backup()
    )
    # MOCK DATA
    paired_devices = ["Trezor Suite"] if ble.is_connected() else []
    bluetooth_version = "2.3.1.1"
    # ###
    firmware_version = ".".join(map(str, utils.VERSION))
    firmware_type = "Bitcoin-only" if utils.BITCOIN_ONLY else "Universal"

    auto_lock_delay = (
        strings.format_autolock_duration(storage_device.get_autolock_delay_ms())
        if config.has_pin()
        else None
    )

    if __debug__:
        log.debug(
            __name__,
            f"device menu, BLE state: {ble.connection_flags()} (peers: {ble.peer_count()})",
        )

    menu_result = await interact(
        trezorui_api.show_device_menu(
            failed_backup=failed_backup,
            paired_devices=paired_devices,
            connected_idx=None,
            bluetooth=True,  # TODO implement bluetooth handling
            pin_code=config.has_pin() if storage_device.is_initialized() else None,
            auto_lock_delay=auto_lock_delay,
            wipe_code=(
                config.has_wipe_code() if storage_device.is_initialized() else None
            ),
            check_backup=storage_device.is_initialized(),
            device_name=(
                (storage_device.get_label() or "Trezor")
                if storage_device.is_initialized()
                else None
            ),
            screen_brightness=(
                TR.brightness__title if storage_device.is_initialized() else None
            ),
            haptic_feedback=(
                storage_device.get_haptic_feedback()
                if (storage_device.is_initialized() and utils.USE_HAPTIC)
                else None
            ),
            led_enabled=(
                storage_device.get_rgb_led()
                if (storage_device.is_initialized() and utils.USE_RGB_LED)
                else None
            ),
            about_items=[
                (TR.homescreen__firmware_version, firmware_version, False),
                (TR.homescreen__firmware_type, firmware_type, False),
                (TR.ble__version, bluetooth_version, False),
            ],
        ),
        "device_menu",
    )
    # Root menu
    if menu_result is DeviceMenuResult.BackupFailed:
        pass  # TODO implement backup failed handling
    # Pair & Connect
    elif menu_result is DeviceMenuResult.DeviceDisconnect:
        pass  # TODO implement device disconnect handling
    elif menu_result is DeviceMenuResult.DevicePair:
        from apps.management.ble.pair_new_device import pair_new_device

        await pair_new_device()
    elif menu_result is DeviceMenuResult.DeviceUnpairAll:
        pass  # TODO implement all devices unpair handling
    elif isinstance(menu_result, tuple):
        # It's a tuple with (result_type, index)
        result_type, index = menu_result
        if result_type is DeviceMenuResult.DeviceConnect:
            pass  # TODO implement device connect handling
        elif result_type is DeviceMenuResult.DeviceUnpair:
            pass  # TODO implement device unpair handling
        else:
            raise RuntimeError(f"Unknown menu {result_type}, {index}")
    # Bluetooth
    elif menu_result is DeviceMenuResult.Bluetooth:
        from trezor.ui.layouts import confirm_action

        turned_on = ble.is_connected()

        await confirm_action(
            "ble__settings",
            TR.words__bluetooth,
            TR.ble__disable if turned_on else TR.ble__enable,
        )
        pass  # TODO implement bluetooth handling
    # Security settings
    elif menu_result is DeviceMenuResult.PinCode:
        from trezor.messages import ChangePin

        from apps.management.change_pin import change_pin

        await change_pin(ChangePin())
    elif menu_result is DeviceMenuResult.PinRemove:
        from trezor.messages import ChangePin

        from apps.management.change_pin import change_pin

        await change_pin(ChangePin(remove=True))
    elif menu_result is DeviceMenuResult.AutoLockDelay:
        from trezor.messages import ApplySettings

        from apps.management.apply_settings import apply_settings

        assert config.has_pin()
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
        assert isinstance(auto_lock_delay_ms, int)
        await apply_settings(
            ApplySettings(
                auto_lock_delay_ms=auto_lock_delay_ms,
            )
        )
    elif menu_result is DeviceMenuResult.WipeCode:
        from trezor.messages import ChangeWipeCode

        from apps.management.change_wipe_code import change_wipe_code

        await change_wipe_code(ChangeWipeCode())
    elif menu_result is DeviceMenuResult.WipeRemove:
        from trezor.messages import ChangeWipeCode

        from apps.management.change_wipe_code import change_wipe_code

        await change_wipe_code(ChangeWipeCode(remove=True))
    elif menu_result is DeviceMenuResult.CheckBackup:
        from trezor.enums import RecoveryType
        from trezor.messages import RecoveryDevice

        from apps.management.recovery_device import recovery_device

        await recovery_device(
            RecoveryDevice(
                type=RecoveryType.DryRun,
            )
        )
    # Device settings
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
    elif menu_result is DeviceMenuResult.ScreenBrightness:
        from trezor.messages import SetBrightness

        from apps.management.set_brightness import set_brightness

        await set_brightness(SetBrightness())
    elif menu_result is DeviceMenuResult.HapticFeedback:
        from trezor.messages import ApplySettings

        from apps.management.apply_settings import apply_settings

        assert storage_device.is_initialized()
        await apply_settings(
            ApplySettings(
                haptic_feedback=not storage_device.get_haptic_feedback(),
            )
        )
    elif menu_result is DeviceMenuResult.LedEnabled:
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
    elif menu_result is DeviceMenuResult.WipeDevice:
        from trezor.messages import WipeDevice

        from apps.management.wipe_device import wipe_device

        await wipe_device(WipeDevice())
    else:
        raise RuntimeError(f"Unknown menu {menu_result}")
