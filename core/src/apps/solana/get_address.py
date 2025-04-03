from typing import TYPE_CHECKING

from trezor.crypto import base58

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaAddress, SolanaGetAddress
    from trezor.wire import MaybeEarlyResponse

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(
    msg: SolanaGetAddress,
    keychain: Keychain,
) -> MaybeEarlyResponse[SolanaAddress]:
    from trezor.messages import SolanaAddress
    from trezor.ui.layouts import show_address, show_continue_in_app
    from trezor.wire import early_response

    from apps.common import paths

    from .get_public_key import derive_public_key

    public_key = derive_public_key(keychain, msg.address_n)
    address = base58.encode(public_key)
    response = SolanaAddress(address=address)

    if msg.show_display:
        from trezor import TR

        await show_address(
            address,
            path=paths.address_n_to_str(msg.address_n),
            chunkify=bool(msg.chunkify),
        )
        return await early_response(
            response, show_continue_in_app(TR.address__confirmed)
        )

    return response
