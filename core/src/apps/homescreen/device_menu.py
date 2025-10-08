import utime
from micropython import const
from typing import TYPE_CHECKING

import storage.device as storage_device
import trezorble as ble
import trezorui_api
from trezor import TR, config, log, utils
from trezor.ui.layouts import interact, raise_if_cancelled
from trezor.wire import ActionCancelled, PinCancelled
from trezorui_api import CANCELLED, DeviceMenuResult

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import ThpPairedCacheEntry

BLE_MAX_BONDS = 8


# Must be in sync with the DeviceMenuId in device_menu.ui
class SubmenuId:
    ROOT = const(0)
    PAIR_AND_CONNECT = const(1)
    SETTINGS = const(2)
    SECURITY = const(3)
    PIN_CODE = const(4)
    AUTO_LOCK = const(5)
    WIPE_CODE = const(6)
    DEVICE = const(7)
    POWER = const(8)


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

        if utils.USE_NRF:
            nrf_version = utils.nrf_get_version()
            bluetooth_version = (
                f"{nrf_version[0]}.{nrf_version[1]}.{nrf_version[2]}.{nrf_version[3]}"
            )
        else:
            bluetooth_version = "0.0.0.0"

        # ###
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
        # Root menu
        if menu_result is DeviceMenuResult.ReviewFailedBackup and backup_failed:
            from trezor.messages import WipeDevice

            from apps.management.wipe_device import wipe_device

            try:
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
            except ActionCancelled:
                init_submenu_idx = SubmenuId.ROOT
            else:
                break
        # Pair & Connect
        elif menu_result is DeviceMenuResult.DisconnectDevice and ble.is_connected():
            init_submenu_idx = SubmenuId.PAIR_AND_CONNECT
            try:
                utils.notify_send(utils.NOTIFY_DISCONNECT)
                utime.sleep_ms(300)
                ble.disconnect()
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.PAIR_AND_CONNECT
        elif menu_result is DeviceMenuResult.PairDevice:
            from trezor.ui.layouts import show_warning

            from apps.management.ble.pair_new_device import pair_new_device

            init_submenu_idx = SubmenuId.PAIR_AND_CONNECT
            # Show warning if Bluetooth is not enabled
            if not ble_enabled:
                try:
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
                except ActionCancelled:
                    continue
                else:
                    ble_enable(True)

            try:
                if len(paired_devices) < BLE_MAX_BONDS:
                    await pair_new_device()
                else:
                    await show_warning(
                        "device_pair",
                        TR.ble__limit_reached,
                        button=TR.buttons__confirm,
                    )
            except ActionCancelled:
                pass
        elif menu_result is DeviceMenuResult.UnpairAllDevices:
            from trezor.messages import BleUnpair

            from apps.management.ble.unpair import unpair

            try:
                await unpair(BleUnpair(all=True))
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.PAIR_AND_CONNECT
        elif isinstance(menu_result, tuple):
            from trezor.messages import BleUnpair

            from apps.management.ble.unpair import unpair

            # It's a tuple with (result_type, index)
            result_type, index = menu_result
            if result_type is DeviceMenuResult.UnpairDevice and index < len(bonds):
                try:
                    await unpair(BleUnpair(addr=bonds[index]))
                except ActionCancelled:
                    pass
                finally:
                    init_submenu_idx = SubmenuId.PAIR_AND_CONNECT
            # Refresh only
            elif result_type is DeviceMenuResult.RefreshMenu:
                init_submenu_idx = index
            else:
                raise RuntimeError(f"Unknown menu {result_type}, {index}")
        # Settings
        elif menu_result is DeviceMenuResult.ToggleBluetooth:
            init_submenu_idx = SubmenuId.SETTINGS
            # Toggle Bluetooth
            ble_enable(not ble_enabled)
        # Security settings
        elif menu_result is DeviceMenuResult.SetOrChangePin and is_initialized:
            from trezor.messages import ChangePin

            from apps.management.change_pin import change_pin

            try:
                await change_pin(ChangePin())
            except (ActionCancelled, PinCancelled):
                pass
            finally:
                init_submenu_idx = SubmenuId.SECURITY
        elif menu_result is DeviceMenuResult.RemovePin and config.has_pin():
            from trezor.messages import ChangePin

            from apps.management.change_pin import change_pin

            try:
                await change_pin(ChangePin(remove=True))
            except (ActionCancelled, PinCancelled):
                pass
            finally:
                init_submenu_idx = SubmenuId.SECURITY
        elif (
            menu_result
            in (DeviceMenuResult.SetAutoLockUSB, DeviceMenuResult.SetAutoLockBattery)
            and config.has_pin()
        ):
            from trezor.messages import ApplySettings

            from apps.management.apply_settings import apply_settings

            try:
                if menu_result is DeviceMenuResult.SetAutoLockUSB:
                    duration_ms = storage_device.get_autolock_delay_ms()
                    min_ms = storage_device.AUTOLOCK_DELAY_USB_MIN_MS
                    max_ms = storage_device.AUTOLOCK_DELAY_USB_MAX_MS
                else:
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
                if menu_result is DeviceMenuResult.SetAutoLockUSB:
                    settings = ApplySettings(
                        auto_lock_delay_ms=auto_lock_delay_ms,
                    )
                else:
                    settings = ApplySettings(
                        auto_lock_delay_battery_ms=auto_lock_delay_ms,
                    )
                await apply_settings(settings)
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.SECURITY
        elif menu_result is DeviceMenuResult.SetOrChangeWipeCode and is_initialized:
            from trezor.messages import ChangeWipeCode

            from apps.management.change_wipe_code import change_wipe_code

            try:
                await change_wipe_code(ChangeWipeCode())
            except (ActionCancelled, PinCancelled):
                pass
            finally:
                init_submenu_idx = SubmenuId.SECURITY
        elif menu_result is DeviceMenuResult.RemoveWipeCode and config.has_wipe_code():
            from trezor.messages import ChangeWipeCode

            from apps.management.change_wipe_code import change_wipe_code

            try:
                await change_wipe_code(ChangeWipeCode(remove=True))
            except (ActionCancelled, PinCancelled):
                pass
            finally:
                init_submenu_idx = SubmenuId.SECURITY
        elif menu_result is DeviceMenuResult.CheckBackup and is_initialized:
            from trezor.enums import RecoveryType
            from trezor.messages import RecoveryDevice

            from apps.management.recovery_device import recovery_device

            try:

                await recovery_device(
                    RecoveryDevice(
                        type=RecoveryType.DryRun,
                    )
                )
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.SECURITY
        # Device settings
        elif menu_result is DeviceMenuResult.SetDeviceName and is_initialized:
            from trezor.messages import ApplySettings

            from apps.management.apply_settings import apply_settings

            try:
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
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.DEVICE
        elif menu_result is DeviceMenuResult.SetBrightness and is_initialized:
            from trezor.messages import SetBrightness

            from apps.management.set_brightness import set_brightness

            try:
                await set_brightness(SetBrightness())
                utils.notify_send(utils.NOTIFY_SETTING_CHANGE)
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.DEVICE
        elif menu_result is DeviceMenuResult.ToggleHaptics and haptic_configurable:
            from trezor import io

            try:
                enable = not storage_device.get_haptic_feedback()
                io.haptic.haptic_set_enabled(enable)
                storage_device.set_haptic_feedback(enable)
                utils.notify_send(utils.NOTIFY_SETTING_CHANGE)
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.DEVICE
        elif menu_result is DeviceMenuResult.ToggleLed and led_configurable:
            from trezor import io

            try:
                enable = not storage_device.get_rgb_led()
                io.rgb_led.rgb_led_set_enabled(enable)
                storage_device.set_rgb_led(enable)
                utils.notify_send(utils.NOTIFY_SETTING_CHANGE)
            except ActionCancelled:
                pass
            finally:
                init_submenu_idx = SubmenuId.DEVICE
        elif menu_result is DeviceMenuResult.WipeDevice:
            from trezor.messages import WipeDevice

            from apps.management.wipe_device import wipe_device

            try:
                await wipe_device(WipeDevice())
            except ActionCancelled:
                init_submenu_idx = SubmenuId.DEVICE
            else:
                break
        # Power settings
        elif menu_result is DeviceMenuResult.TurnOff:
            from trezor import io

            io.pm.hibernate()
            raise RuntimeError
        elif menu_result is DeviceMenuResult.Reboot:
            from trezor.utils import reboot_to_bootloader

            # Empty boot command results to a normal reboot
            reboot_to_bootloader()
            raise RuntimeError
        elif menu_result is DeviceMenuResult.RebootToBootloader:
            from trezor.enums import BootCommand
            from trezor.utils import reboot_to_bootloader

            reboot_to_bootloader(BootCommand.STOP_AND_WAIT)
            raise RuntimeError
        elif menu_result is CANCELLED:
            return
        else:
            raise RuntimeError(f"Unknown menu {menu_result}")
