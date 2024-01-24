from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BLEAuthKey, BLEPairingRequest


async def pairing_request(_msg: BLEPairingRequest) -> BLEAuthKey:
    from trezor.messages import BLEAuthKey
    from trezor.ui.layouts import request_pin_on_device
    from trezor.wire import context

    pin = await context.with_context(
        None, request_pin_on_device("PAIRING", None, True, False)
    )

    if len(pin) != 6:
        pin = "000000"

    return BLEAuthKey(key=pin.encode())
