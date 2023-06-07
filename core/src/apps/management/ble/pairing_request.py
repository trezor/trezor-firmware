from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import (
        AuthKey,
        PairingRequest,
    )


async def pairing_request(_msg: PairingRequest) -> AuthKey:
    from trezor.messages import (
        AuthKey,
    )
    from trezor.ui.layouts import request_pin_on_device

    pin = await request_pin_on_device("PAIRING", None, True, False, True)

    if len(pin) != 6:
        pin = "000000"

    return AuthKey(key=pin.encode())
