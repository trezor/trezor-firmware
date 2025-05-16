import storage.device
import trezorui_api
from trezor import utils
from trezor.ui.layouts import raise_if_not_confirmed


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
    else:
        raise RuntimeError(f"Unknown menu {menu_result}")
