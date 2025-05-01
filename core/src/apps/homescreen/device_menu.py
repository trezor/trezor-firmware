import storage.device
import trezorui_api
from trezor import TR, config, utils
from trezor.ui.layouts import raise_if_not_confirmed
from trezor.ui.layouts.common import interact
from trezor.wire import ActionCancelled, NotInitialized, ProcessError


async def _prompt_auto_lock_delay() -> int:
    DEFAUTL_AUTOLOCK_DELAY_S = 300  # 5 minutes
    MIN_AUTOLOCK_DELAY_S = 10  # 10 seconds
    MAX_AUTOLOCK_DELAY_S = 518400  # 6 days
    result = await interact(
        trezorui_api.request_number(
            title=TR.auto_lock__title,
            count=DEFAUTL_AUTOLOCK_DELAY_S,
            min_count=MIN_AUTOLOCK_DELAY_S,
            max_count=MAX_AUTOLOCK_DELAY_S,
            time_unit=True,
            description=TR.auto_lock__description,
        ),
        br_name=None,
    )

    if result is not trezorui_api.CANCELLED:
        assert isinstance(result, int)
        return result
    else:
        raise ActionCancelled  # user cancelled request number prompt


async def handle_device_menu() -> None:
    # MOCK DATA
    failed_backup = True
    battery_percentage = 22
    paired_devices = ["Trezor Suite"]
    # ###
    firmware_version = ".".join(map(str, utils.VERSION))
    device_name = storage.device.get_label() or "Trezor"

    menu_result = await raise_if_not_confirmed(
        trezorui_api.show_device_menu(
            failed_backup=failed_backup,
            battery_percentage=battery_percentage,
            paired_devices=paired_devices,
            firmware_version=firmware_version,
            device_name=device_name,
        ),
        None,
    )
    if menu_result == "DevicePair":
        from apps.management.ble.pair_new_device import pair_new_device

        await pair_new_device()
    elif menu_result == "ScreenBrightness":
        from trezor.ui.layouts import set_brightness

        await set_brightness()
    elif menu_result == "WipeDevice":
        from trezor.messages import WipeDevice

        from apps.management.wipe_device import wipe_device

        await wipe_device(WipeDevice())
    elif menu_result == "AutoLockDelay":
        import storage.device as storage_device

        if not storage_device.is_initialized():
            raise NotInitialized("Device is not initialized")

        if not config.has_pin():
            raise ProcessError("Set up a PIN first")

        auto_lock_delay_s = await _prompt_auto_lock_delay()

        if auto_lock_delay_s * 1000 < storage_device.AUTOLOCK_DELAY_MINIMUM:
            raise ProcessError("Auto-lock delay too short")
        if auto_lock_delay_s * 1000 > storage_device.AUTOLOCK_DELAY_MAXIMUM:
            raise ProcessError("Auto-lock delay too long")

        storage_device.set_autolock_delay_ms(auto_lock_delay_s * 1000)
    else:
        raise RuntimeError(f"Unknown menu {menu_result}")
