import trezorble as ble
import trezorui_api
from storage import device as storage_device
from trezor import utils
from trezor.crypto import random
from trezor.ui.layouts import CONFIRMED, interact
from trezor.wire import ActionCancelled


def _end_pairing() -> None:
    if ble.peer_count() > 0:
        ble.start_advertising(True, storage_device.get_label())
    else:
        ble.stop_advertising()


def _default_ble_name() -> str:
    """Return model name and three random letters.

    >>> n1 = _default_ble_name()
    >>> n1.startswith(utils.MODE_FULL_NAME)
    True
    >>> n2 = _default_ble_name()
    >>> n2.startswith(utils.MODE_FULL_NAME)
    True
    >>> n1 == n2
    False
    """
    charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    random_chars = "".join(charset[random.uniform(len(charset))] for _ in range(3))
    return f"{utils.MODEL_FULL_NAME} ({random_chars})"


async def pair_new_device() -> None:
    label = storage_device.get_label() or _default_ble_name()
    ble.start_advertising(False, label)
    try:
        code = await interact(
            trezorui_api.show_pairing_device_name(
                device_name=label,
            ),
            None,
        )
        if not isinstance(code, int):
            raise ActionCancelled

        try:
            result = await interact(
                trezorui_api.show_ble_pairing_code(
                    title="Bluetooth pairing",
                    description="Pairing code match?",
                    code=f"{code:0>6}",
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
