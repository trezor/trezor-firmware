import trezorui_api
from trezor.ui.layouts import interact


async def pair_new_device() -> None:
    label = "Trezor T3W1"
    await interact(
        trezorui_api.show_pairing_device_name(device_name=label),
        None,
        raise_on_cancel=None,  # for UI testing
    )

    code = 12345
    await interact(
        trezorui_api.show_pairing_code(code=f"{code:0>6}"),
        None,
    )
