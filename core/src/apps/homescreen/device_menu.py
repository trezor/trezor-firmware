from typing import TYPE_CHECKING
import storage.device as storage_device
import trezorble as ble
import trezorui_api
from trezor import TR, config, log, utils
from trezor.ui.layouts import interact
from trezorui_api import DeviceMenuResult

if TYPE_CHECKING:
    from trezor.ui.layouts import PropertyType


async def handle_device_menu() -> None:
    from trezor import strings

    # TODO: unify with notification handling in `apps/homescreen/__init__.py:homescreen()`
    failed_backup = (
        storage_device.is_initialized() and storage_device.unfinished_backup()
    )
    # MOCK DATA
    paired_devices = ["Trezor Suite"] if ble.is_connected() else []
    # ###
    about_items: list[PropertyType] = [
        (TR.homescreen__firmware_version, ".".join(map(str, utils.VERSION)), False),
        (
            TR.homescreen__firmware_type,
            "Bitcoin-only" if utils.BITCOIN_ONLY else "Universal",
            False,
        ),
    ]

    device_name = storage_device.get_label() or "Trezor"

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
            device_name=device_name,
            about_items=about_items,
            paired_devices=paired_devices,
            auto_lock_delay=auto_lock_delay,
            screen_brightness=(
                TR.brightness__title if storage_device.is_initialized() else None
            ),
            haptic_feedback=(
                storage_device.get_haptic_feedback()
                if (storage_device.is_initialized() and utils.USE_HAPTIC)
                else None
            ),
            led=None,  # TODO: implement LED setting
            bluetooth=None,  # TODO: implement BLE setting
        ),
        "device_menu",
    )

    if menu_result is DeviceMenuResult.DevicePair:
        from apps.management.ble.pair_new_device import pair_new_device

        await pair_new_device()
    elif menu_result is DeviceMenuResult.ScreenBrightness:
        from apps.management.set_brightness import set_brightness
        from trezor.messages import SetBrightness

        await set_brightness(SetBrightness())
    elif menu_result is DeviceMenuResult.WipeDevice:
        from trezor.messages import WipeDevice
        from apps.management.wipe_device import wipe_device

        await wipe_device(WipeDevice())
    elif menu_result is DeviceMenuResult.AutoLockDelay:
        from apps.management.apply_settings import apply_settings
        from trezor.messages import ApplySettings

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

    elif menu_result is DeviceMenuResult.HapticFeedback:
        from apps.management.apply_settings import apply_settings
        from trezor.messages import ApplySettings

        assert storage_device.is_initialized()
        await apply_settings(
            ApplySettings(
                haptic_feedback=not storage_device.get_haptic_feedback(),
            )
        )

    elif menu_result is DeviceMenuResult.Led:
        pass  # TODO: implement LED setting

    elif menu_result is DeviceMenuResult.Bluetooth:
        pass  # TODO: implement BLE setting

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
