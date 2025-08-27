import storage.device as storage_device
import trezorble as ble
import trezorui_api
from trezor import TR, config, log, utils
from trezor.ui.layouts import interact
from trezorui_api import DeviceMenuResult

MAX_PAIRED_DEVICES = 4


async def handle_device_menu() -> None:
    from trezor import strings

    is_initialized = storage_device.is_initialized()
    led_configurable = is_initialized and utils.USE_RGB_LED
    haptic_configurable = is_initialized and utils.USE_HAPTIC
    failed_backup = is_initialized and storage_device.unfinished_backup()
    # MOCK DATA
    paired_devices = ["Trezor Suite"]
    connected_idx = 0 if ble.is_connected() else None
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
            connected_idx=connected_idx,
            bluetooth=True,  # TODO implement bluetooth handling
            pin_code=config.has_pin() if is_initialized else None,
            auto_lock_delay=auto_lock_delay,
            wipe_code=config.has_wipe_code() if is_initialized else None,
            check_backup=is_initialized,
            device_name=(
                (storage_device.get_label() or utils.MODEL_FULL_NAME)
                if is_initialized
                else None
            ),
            screen_brightness=TR.brightness__title if is_initialized else None,
            haptic_feedback=(
                storage_device.get_haptic_feedback() if haptic_configurable else None
            ),
            led_enabled=(storage_device.get_rgb_led() if led_configurable else None),
            about_items=[
                (TR.homescreen__firmware_version, firmware_version, False),
                (TR.homescreen__firmware_type, firmware_type, False),
                (TR.ble__version, bluetooth_version, False),
            ],
        ),
        "device_menu",
    )
    # Root menu
    if menu_result is DeviceMenuResult.BackupFailed and failed_backup:
        from trezor.messages import WipeDevice
        from trezor.ui.layouts import raise_if_cancelled

        from apps.management.wipe_device import wipe_device

        await raise_if_cancelled(
            trezorui_api.show_warning(
                title=TR.homescreen__title_backup_failed,
                button=TR.words__wipe,
                description=TR.wipe__start_again,
                danger=True,
            ),
            "prompt_device_wipe",
        )

        await wipe_device(WipeDevice())
    # Pair & Connect
    elif menu_result is DeviceMenuResult.DeviceDisconnect:
        from trezor.ui.layouts import confirm_action

        await confirm_action(
            "device_disconnect",
            "device_disconnect",
            "disconnect currently connected device?",
        )
        # TODO implement device disconnect handling
    elif menu_result is DeviceMenuResult.DevicePair:
        from trezor.ui.layouts import show_warning

        from apps.management.ble.pair_new_device import pair_new_device

        if len(paired_devices) < MAX_PAIRED_DEVICES:
            await pair_new_device()
        else:
            await show_warning(
                "device_pair",
                "Limit of paired devices reached.",
                button=TR.buttons__continue,
            )
    elif menu_result is DeviceMenuResult.DeviceUnpairAll:
        from trezor.messages import BleUnpair

        from apps.management.ble.unpair import unpair

        await unpair(BleUnpair(all=True))
    elif isinstance(menu_result, tuple):
        from trezor.ui.layouts import confirm_action

        # It's a tuple with (result_type, index)
        result_type, index = menu_result
        if result_type is DeviceMenuResult.DeviceConnect:
            await confirm_action(
                "device_connect",
                "device_connect",
                f"connect {index} device?",
                "The currently connected device will be disconnected.",
            )
            # TODO implement device connect handling
        elif result_type is DeviceMenuResult.DeviceUnpair:
            await confirm_action(
                "device_unpair",
                "device_unpair",
                f"unpair {index} device?",
            )
            # TODO implement device unpair handling
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
    elif menu_result is DeviceMenuResult.PinCode and is_initialized:
        from trezor.messages import ChangePin

        from apps.management.change_pin import change_pin

        await change_pin(ChangePin())
    elif menu_result is DeviceMenuResult.PinRemove and config.has_pin():
        from trezor.messages import ChangePin

        from apps.management.change_pin import change_pin

        await change_pin(ChangePin(remove=True))
    elif menu_result is DeviceMenuResult.AutoLockDelay and config.has_pin():
        from trezor.messages import ApplySettings

        from apps.management.apply_settings import apply_settings

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
        # Necessary for the style check not to raise type error
        assert isinstance(auto_lock_delay_ms, int)
        await apply_settings(
            ApplySettings(
                auto_lock_delay_ms=auto_lock_delay_ms,
            )
        )
    elif menu_result is DeviceMenuResult.WipeCode and is_initialized:
        from trezor.messages import ChangeWipeCode

        from apps.management.change_wipe_code import change_wipe_code

        await change_wipe_code(ChangeWipeCode())
    elif menu_result is DeviceMenuResult.WipeRemove and config.has_wipe_code():
        from trezor.messages import ChangeWipeCode

        from apps.management.change_wipe_code import change_wipe_code

        await change_wipe_code(ChangeWipeCode(remove=True))
    elif menu_result is DeviceMenuResult.CheckBackup and is_initialized:
        from trezor.enums import RecoveryType
        from trezor.messages import RecoveryDevice

        from apps.management.recovery_device import recovery_device

        await recovery_device(
            RecoveryDevice(
                type=RecoveryType.DryRun,
            )
        )
    # Device settings
    elif menu_result is DeviceMenuResult.DeviceName and is_initialized:
        from trezor.messages import ApplySettings

        from apps.management.apply_settings import apply_settings

        label = await interact(
            trezorui_api.request_string(
                prompt=TR.device_name__enter,
                max_len=storage_device.LABEL_MAXLENGTH,
                allow_empty=True,
                prefill=storage_device.get_label(),
            ),
            "device_name",
        )
        # Necessary for the style check not to raise type error
        assert isinstance(label, str)
        await apply_settings(ApplySettings(label=label))
    elif menu_result is DeviceMenuResult.ScreenBrightness and is_initialized:
        from trezor.messages import SetBrightness

        from apps.management.set_brightness import set_brightness

        await set_brightness(SetBrightness())
    elif menu_result is DeviceMenuResult.HapticFeedback and haptic_configurable:
        from trezor.messages import ApplySettings

        from apps.management.apply_settings import apply_settings

        await apply_settings(
            ApplySettings(
                haptic_feedback=not storage_device.get_haptic_feedback(),
            )
        )
    elif menu_result is DeviceMenuResult.LedEnabled and led_configurable:
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
