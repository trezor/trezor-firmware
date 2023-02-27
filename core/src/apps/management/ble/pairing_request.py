from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.messages import (
        AuthKey,
        PairingRequest,
    )


async def pairing_request(ctx: GenericContext, _msg: PairingRequest) -> AuthKey:
    from trezor.messages import (
        AuthKey,
    )
    from trezor.ui.layouts import request_pin_on_device

    pin = await request_pin_on_device(ctx, "PAIRING", None, True, False, True)

    return AuthKey(key=pin.encode())
