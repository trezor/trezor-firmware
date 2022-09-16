from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import BinanceGetAddress, BinanceAddress
    from trezor.wire import Context
    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(
    ctx: Context, msg: BinanceGetAddress, keychain: Keychain
) -> BinanceAddress:
    from trezor.messages import BinanceAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths

    from .helpers import address_from_public_key

    HRP = "bnb"
    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(ctx, keychain, address_n)

    node = keychain.derive(address_n)
    pubkey = node.public_key()
    address = address_from_public_key(pubkey, HRP)
    if msg.show_display:
        title = paths.address_n_to_str(address_n)
        await show_address(ctx, address, title=title)

    return BinanceAddress(address=address)
