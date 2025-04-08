import trezorble as ble
import trezorui_api
from storage import device as storage_device
from trezor.ui.layouts import CONFIRMED, raise_if_not_confirmed
from trezor.wire import ActionCancelled


def _end_pairing() -> None:
    if ble.peer_count() > 0:
        ble.start_advertising(True, storage_device.get_label())
    else:
        ble.stop_advertising()


async def pair_new_device() -> None:
    label = storage_device.get_label() or "Trezor T3W1"
    ble.start_advertising(False, label)
    try:
        code = await raise_if_not_confirmed(
            trezorui_api.show_pairing_device_name(
                device_name=label,
            ),
            None,
        )
        if not isinstance(code, int):
            raise ActionCancelled

        result = await raise_if_not_confirmed(
            trezorui_api.show_pairing_code(
                code=f"{code:0>6}",
            ),
            None,
        )
        if result is CONFIRMED:
            ble.allow_pairing(code)
        else:
            ble.reject_pairing()
    finally:
        _end_pairing()
