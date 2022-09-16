from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import RippleGetAddress, RippleAddress
    from apps.common.keychain import Keychain
    from trezor.wire import Context


@auto_keychain(__name__)
async def get_address(
    ctx: Context, msg: RippleGetAddress, keychain: Keychain
) -> RippleAddress:
    # NOTE: local imports here saves 20 bytes
    from trezor.messages import RippleAddress
    from trezor.ui.layouts import show_address
    from apps.common import paths
    from .helpers import address_from_public_key

    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    address = address_from_public_key(pubkey)

    if msg.show_display:
        title = paths.address_n_to_str(msg.address_n)
        await show_address(ctx, address, title=title)

    return RippleAddress(address=address)
