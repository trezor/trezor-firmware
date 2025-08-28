import trezorble as ble
import trezorui_api
from storage import device as storage_device
from trezor import TR, utils
from trezor.crypto import random
from trezor.ui.layouts import CONFIRMED, interact
from trezor.wire import ActionCancelled


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

    # Placeholders are coming from translations in form of {0}
    template_str = "{0}"
    description = TR.ble__device_name_template
    assert template_str in description

    begin, _separator, end = description.partition(template_str)

    result = None
    try:
        code = await interact(
            trezorui_api.show_pairing_device_name(
                title=TR.ble__pair_new,
                items=(begin, (True, label), end),
                verb=TR.ble__continue_on_host,
            ),
            None,
        )
        if not isinstance(code, int):
            raise ActionCancelled

        try:
            result = await interact(
                trezorui_api.show_ble_pairing_code(
                    title=TR.ble__pairing,
                    description=TR.ble__pair_code_match,
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
        if result is not CONFIRMED:
            ble.reject_pairing()
        ble.set_name(storage_device.get_label())
