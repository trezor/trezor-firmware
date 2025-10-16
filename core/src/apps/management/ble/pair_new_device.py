import trezorble as ble
import trezorui_api
from storage import device as storage_device
from trezor import utils
from trezor.crypto import random
from trezor.ui.layouts import CONFIRMED, interact
from trezor.wire import ActionCancelled


def _default_ble_name() -> str:
    """Return model name and three random characters.

    >>> n1 = _default_ble_name()
    >>> n1.startswith(utils.MODE_FULL_NAME)
    True
    >>> n2 = _default_ble_name()
    >>> n2.startswith(utils.MODE_FULL_NAME)
    True
    >>> n1 == n2
    False
    """
    digits = "0123456789"
    uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    random_chars = "".join(
        [
            digits[random.uniform(len(digits))],
            uppercase[random.uniform(len(uppercase))],
            digits[random.uniform(len(digits))],
        ]
    )

    return f"{utils.MODEL_FULL_NAME} ({random_chars})"


async def pair_new_device() -> None:
    from trezor import TR

    label = storage_device.get_label() or _default_ble_name()
    ble.start_advertising(False, label)
    result = None
    try:
        code = await interact(
            trezorui_api.show_pairing_device_name(
                description=TR.thp__pair_name,
                device_name=label,
            ),
            None,
        )
        if not isinstance(code, int):
            raise ActionCancelled

        result = await interact(
            trezorui_api.show_ble_pairing_code(
                title=TR.ble__pairing_title,
                description=TR.ble__pairing_match,
                code=f"{code:0>6}",
            ),
            None,
        )
        if result is CONFIRMED:
            ble.allow_pairing(code)

        # wait for the host code confirmation
        await interact(trezorui_api.wait_ble_host_confirmation(), None)
    finally:
        if result is not CONFIRMED:
            ble.reject_pairing()
        ble.set_name(storage_device.get_label())
