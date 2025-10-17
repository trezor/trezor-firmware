import utime
from typing import TYPE_CHECKING

import storage.device as storage_device
import trezorble as ble
import trezorui_api
from trezor import TR, config, log, utils
from trezor.ui.layouts import interact, raise_if_not_confirmed
from trezor.wire import ActionCancelled, PinCancelled
from trezorui_api import CANCELLED, DeviceMenuResult

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import ThpPairedCacheEntry


# Idicates that menu should be closed and return to homescreen.
class ExitDeviceMenu(Exception):
    pass


def _get_hostinfo(
    ble_addr: AnyBytes, hostname_map: dict[AnyBytes, ThpPairedCacheEntry]
) -> tuple[str, tuple[str, str] | None]:
    # Internal MAC address representation is using reversed byte order.
    mac = ":".join(f"{byte:02X}" for byte in reversed(ble_addr))
    if hostinfo := hostname_map.get(ble_addr):
        return (mac, (hostinfo.host_name, hostinfo.app_name))
    return (mac, None)


def _find_device(connected_addr: bytes | None, bonds: list[bytes]) -> int | None:
    if connected_addr is None:
        return None
    for i, bond in enumerate(bonds):
        if bond == connected_addr:
            return i
    return None


def get_auto_lock_delay() -> tuple[str, str] | None:
    from trezor import strings

    if not config.has_pin():
        return None
    autolock_delay_batt = storage_device.get_autolock_delay_battery_ms()
    autolock_delay_usb = storage_device.get_autolock_delay_ms()

    autolock_delay_batt_fmg = strings.format_autolock_duration(autolock_delay_batt)
    autolock_delay_usb_fmt = strings.format_autolock_duration(autolock_delay_usb)

    return (autolock_delay_batt_fmg, autolock_delay_usb_fmt)


def ble_enable(enable: bool) -> None:
    ble.set_enabled(enable)
    storage_device.set_ble(enable)


async def handle_device_menu() -> None:

    assert utils.USE_THP and utils.USE_BLE

    from trezor.wire.thp import paired_cache

    init_submenu_idx = None

    # Remain in the device loop until the menu is explicitly closed
    while True:

        is_initialized = storage_device.is_initialized()
        led_configurable = is_initialized and utils.USE_RGB_LED
        haptic_configurable = is_initialized and utils.USE_HAPTIC
        backup_failed = is_initialized and storage_device.unfinished_backup()
        backup_needed = is_initialized and storage_device.needs_backup()
        backup_finished = (
            is_initialized
            and not storage_device.needs_backup()
            and not storage_device.unfinished_backup()
            and not storage_device.no_backup()
        )

        bonds = ble.get_bonds()
        if __debug__:
            log.debug(__name__, "bonds: %s", bonds)
        ble_enabled = ble.get_enabled()
        connected_addr = ble.connected_addr()
        connected_idx = _find_device(connected_addr, bonds) if ble_enabled else None
        if __debug__:
            log.debug(__name__, "connected: %s (%s)", connected_addr, connected_idx)
        hostname_map = {e.mac_addr: e for e in paired_cache.load()}
        paired_devices = [_get_hostinfo(bond, hostname_map) for bond in bonds]

        # versions used in "About" screen, emulator uses dummy versions for fixtures
        if utils.EMULATOR or not utils.USE_NRF:
            bluetooth_version = "0.0.0.0"
        else:
            nrf_version = utils.nrf_get_version()
            bluetooth_version = (
                f"{nrf_version[0]}.{nrf_version[1]}.{nrf_version[2]}.{nrf_version[3]}"
            )
        if utils.EMULATOR:
            firmware_version = "0.0.0.0"
        else:
            firmware_version = ".".join(map(str, utils.VERSION))

        firmware_type = "Bitcoin-only" if utils.BITCOIN_ONLY else "Universal"

        menu_result = await interact(
            trezorui_api.show_device_menu(
                init_submenu_idx=init_submenu_idx,
                backup_failed=backup_failed,
                backup_needed=backup_needed,
                ble_enabled=ble_enabled,
                paired_devices=paired_devices,
                connected_idx=connected_idx,
                pin_enabled=config.has_pin() if is_initialized else None,
                auto_lock=get_auto_lock_delay(),
                wipe_code_enabled=(
                    config.has_wipe_code()
                    if (is_initialized and config.has_pin())
                    else None
                ),
                backup_check_allowed=backup_finished,
                device_name=(
                    (storage_device.get_label() or utils.MODEL_FULL_NAME)
                    if is_initialized
                    else None
                ),
                brightness=TR.brightness__title if is_initialized else None,
                haptics_enabled=(
                    storage_device.get_haptic_feedback()
                    if haptic_configurable
                    else None
                ),
                led_enabled=(
                    storage_device.get_rgb_led() if led_configurable else None
                ),
                about_items=[
                    (TR.homescreen__firmware_version, firmware_version, False),
                    (TR.homescreen__firmware_type, firmware_type, False),
                    (TR.ble__version, bluetooth_version, False),
                ],
            ),
            "device_menu",
            raise_on_cancel=None,
        )

        if menu_result is CANCELLED:
            return

        if not isinstance(menu_result, tuple) or len(menu_result) != 3:
            raise RuntimeError(f"Unknown menu {menu_result}")

        action, arg, parent_submenu_idx = menu_result
        handler = _MENU_HANDLERS.get(action)
        if not handler:
            raise RuntimeError(f"Unknown menu {menu_result}")

        # special handling
        if action == DeviceMenuResult.RefreshMenu:
            init_submenu_idx = arg
            continue

        try:
            if arg is None:
                await handler()
            else:
                await handler(arg)
        except ExitDeviceMenu:
            break
        except (ActionCancelled, PinCancelled):
            # return to the submenu if flow was cancelled
            continue
        finally:
            # return to submenu on success or cancellation
            init_submenu_idx = parent_submenu_idx


async def handle_ReviewFailedBackup() -> None:
    from trezor.messages import WipeDevice

    from apps.management.wipe_device import wipe_device

    is_initialized = storage_device.is_initialized()
    backup_failed = is_initialized and storage_device.unfinished_backup()
    utils.ensure(backup_failed)

    await raise_if_not_confirmed(
        trezorui_api.show_warning(
            title=TR.homescreen__title_backup_failed,
            button=TR.words__wipe,
            description=TR.wipe__start_again,
            danger=True,
        ),
        "prompt_device_wipe",
    )
    await wipe_device(WipeDevice())
    raise ExitDeviceMenu  # return to homescreen


async def handle_DisconnectDevice() -> None:
    utils.ensure(ble.is_connected())

    utils.notify_send(utils.NOTIFY_DISCONNECT)
    utime.sleep_ms(300)
    ble.disconnect()


async def handle_PairDevice() -> None:
    from trezor.ui.layouts import show_warning
    from trezor.wire.thp import paired_cache

    from apps.management.ble.pair_new_device import pair_new_device

    # Show warning if Bluetooth is not enabled
    if not ble.get_enabled():
        await interact(
            trezorui_api.show_warning(
                title=TR.words__important,
                description=TR.ble__must_be_enabled,
                button=TR.buttons__turn_on,
                allow_cancel=True,
                danger=False,
            ),
            "enable_bluetooth",
        )
        ble_enable(True)

    hostname_map = {e.mac_addr: e for e in paired_cache.load()}
    paired_devices = [_get_hostinfo(bond, hostname_map) for bond in ble.get_bonds()]
    if len(paired_devices) < ble.MAX_BONDS:
        await pair_new_device()
    else:
        await show_warning(
            "device_pair",
            TR.ble__limit_reached,
            button=TR.buttons__confirm,
        )


async def handle_UnpairAllDevices() -> None:
    from trezor.messages import BleUnpair

    from apps.management.ble.unpair import unpair

    await unpair(BleUnpair(all=True))


async def handle_UnpairDevice(index: int) -> None:
    from trezor.messages import BleUnpair

    from apps.management.ble.unpair import unpair

    bonds = ble.get_bonds()
    if index < len(bonds):
        await unpair(BleUnpair(addr=bonds[index]))


async def handle_ToggleBluetooth() -> None:
    ble_enable(not ble.get_enabled())


async def handle_SetOrChangePin() -> None:
    from trezor.messages import ChangePin

    from apps.management.change_pin import change_pin

    utils.ensure(storage_device.is_initialized())

    await change_pin(ChangePin())


async def handle_RemovePin() -> None:
    from trezor.messages import ChangePin

    from apps.management.change_pin import change_pin

    utils.ensure(config.has_pin())

    await change_pin(ChangePin(remove=True))


async def handle_SetAutoLockUSB() -> None:
    from trezor.messages import ApplySettings

    from apps.management.apply_settings import apply_settings

    utils.ensure(config.has_pin())

    duration_ms = storage_device.get_autolock_delay_ms()
    min_ms = storage_device.AUTOLOCK_DELAY_USB_MIN_MS
    max_ms = storage_device.AUTOLOCK_DELAY_USB_MAX_MS

    auto_lock_delay_ms = await interact(
        trezorui_api.request_duration(
            title=TR.auto_lock__title,
            duration_ms=duration_ms,
            min_ms=min_ms,
            max_ms=max_ms,
            description=TR.auto_lock__description,
        ),
        br_name=None,
    )
    # Necessary for the style check not to raise type error
    assert isinstance(auto_lock_delay_ms, int)
    settings = ApplySettings(
        auto_lock_delay_ms=auto_lock_delay_ms,
    )
    await apply_settings(settings)


async def handle_SetAutoLockBattery() -> None:
    from trezor.messages import ApplySettings

    from apps.management.apply_settings import apply_settings

    utils.ensure(config.has_pin())

    duration_ms = storage_device.get_autolock_delay_battery_ms()
    min_ms = storage_device.AUTOLOCK_DELAY_BATT_MIN_MS
    max_ms = storage_device.AUTOLOCK_DELAY_BATT_MAX_MS

    auto_lock_delay_ms = await interact(
        trezorui_api.request_duration(
            title=TR.auto_lock__title,
            duration_ms=duration_ms,
            min_ms=min_ms,
            max_ms=max_ms,
            description=TR.auto_lock__description,
        ),
        br_name=None,
    )
    # Necessary for the style check not to raise type error
    assert isinstance(auto_lock_delay_ms, int)
    settings = ApplySettings(
        auto_lock_delay_battery_ms=auto_lock_delay_ms,
    )
    await apply_settings(settings)


async def handle_SetOrChangeWipeCode() -> None:
    from trezor.messages import ChangeWipeCode

    from apps.management.change_wipe_code import change_wipe_code

    utils.ensure(storage_device.is_initialized())

    await change_wipe_code(ChangeWipeCode())


async def handle_RemoveWipeCode() -> None:
    from trezor.messages import ChangeWipeCode

    from apps.management.change_wipe_code import change_wipe_code

    utils.ensure(config.has_wipe_code())

    await change_wipe_code(ChangeWipeCode(remove=True))


async def handle_CheckBackup() -> None:
    from trezor.enums import RecoveryType
    from trezor.messages import RecoveryDevice

    from apps.management.recovery_device import recovery_device

    utils.ensure(storage_device.is_initialized())

    await recovery_device(
        RecoveryDevice(
            type=RecoveryType.DryRun,
        )
    )


async def handle_SetDeviceName() -> None:
    from trezor.messages import ApplySettings

    from apps.management.apply_settings import apply_settings

    utils.ensure(storage_device.is_initialized())

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


async def handle_SetBrightness() -> None:
    from trezor.messages import SetBrightness

    from apps.management.set_brightness import set_brightness

    utils.ensure(storage_device.is_initialized())

    await set_brightness(SetBrightness())
    utils.notify_send(utils.NOTIFY_SETTING_CHANGE)


async def handle_ToggleHaptics() -> None:
    from trezor import io

    utils.ensure(storage_device.is_initialized() and utils.USE_HAPTIC)

    enable = not storage_device.get_haptic_feedback()
    io.haptic.haptic_set_enabled(enable)
    storage_device.set_haptic_feedback(enable)
    utils.notify_send(utils.NOTIFY_SETTING_CHANGE)


async def handle_ToggleLed() -> None:
    from trezor import io

    utils.ensure(storage_device.is_initialized() and utils.USE_RGB_LED)

    enable = not storage_device.get_rgb_led()
    io.rgb_led.rgb_led_set_enabled(enable)
    storage_device.set_rgb_led(enable)
    utils.notify_send(utils.NOTIFY_SETTING_CHANGE)


async def handle_WipeDevice() -> None:
    from trezor.messages import WipeDevice

    from apps.management.wipe_device import wipe_device

    await wipe_device(WipeDevice())
    raise ExitDeviceMenu  # return to homescreen


async def handle_TurnOff() -> None:
    from trezor import io

    io.pm.hibernate()
    raise RuntimeError


async def handle_Reboot() -> None:
    from trezor.utils import reboot

    reboot()
    raise RuntimeError


async def handle_RebootToBootloader() -> None:
    from trezor.utils import reboot_to_bootloader

    reboot_to_bootloader()
    raise RuntimeError


_MENU_HANDLERS = {
    DeviceMenuResult.ReviewFailedBackup: handle_ReviewFailedBackup,
    DeviceMenuResult.DisconnectDevice: handle_DisconnectDevice,
    DeviceMenuResult.PairDevice: handle_PairDevice,
    DeviceMenuResult.UnpairAllDevices: handle_UnpairAllDevices,
    DeviceMenuResult.UnpairDevice: handle_UnpairDevice,
    DeviceMenuResult.ToggleBluetooth: handle_ToggleBluetooth,
    DeviceMenuResult.SetOrChangePin: handle_SetOrChangePin,
    DeviceMenuResult.RemovePin: handle_RemovePin,
    DeviceMenuResult.SetAutoLockUSB: handle_SetAutoLockUSB,
    DeviceMenuResult.SetAutoLockBattery: handle_SetAutoLockBattery,
    DeviceMenuResult.SetOrChangeWipeCode: handle_SetOrChangeWipeCode,
    DeviceMenuResult.RemoveWipeCode: handle_RemoveWipeCode,
    DeviceMenuResult.CheckBackup: handle_CheckBackup,
    DeviceMenuResult.SetDeviceName: handle_SetDeviceName,
    DeviceMenuResult.SetBrightness: handle_SetBrightness,
    DeviceMenuResult.ToggleHaptics: handle_ToggleHaptics,
    DeviceMenuResult.ToggleLed: handle_ToggleLed,
    DeviceMenuResult.WipeDevice: handle_WipeDevice,
    DeviceMenuResult.TurnOff: handle_TurnOff,
    DeviceMenuResult.Reboot: handle_Reboot,
    DeviceMenuResult.RebootToBootloader: handle_RebootToBootloader,
}
