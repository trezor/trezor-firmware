import trezorble as ble
import trezorui_api
from storage import device as storage_device
from trezor import utils
from trezor.ui.layouts import CONFIRMED, raise_if_not_confirmed
from trezor.wire import ActionCancelled


def _end_pairing() -> None:
    if ble.peer_count() > 0:
        ble.start_advertising(True, storage_device.get_label())
    else:
        ble.stop_advertising()


async def pair_new_device() -> None:
    label = storage_device.get_label() or utils.MODEL_FULL_NAME
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

        try:
            result = await raise_if_not_confirmed(
                trezorui_api.show_pairing_code(
                    title="Bluetooth pairing",
                    description="Pairing code match?",
                    code=f"{code:0>6}",
                    button=True,
                ),
                None,
            )
        except Exception:
            ble.reject_pairing()
            raise
        else:
            if result is CONFIRMED:
                ble.allow_pairing(code)
    finally:
        _end_pairing()
