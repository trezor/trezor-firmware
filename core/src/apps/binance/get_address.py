from typing import TYPE_CHECKING

from trezor.messages import BinanceAddress, BinanceGetAddress
from trezor.ui.layouts import show_address

from apps.common import paths
from apps.common.keychain import Keychain, auto_keychain

from .helpers import address_from_public_key

if TYPE_CHECKING:
    from trezor.wire import Context


@auto_keychain(__name__)
async def get_address(
    ctx: Context, msg: BinanceGetAddress, keychain: Keychain
) -> BinanceAddress:
    HRP = "bnb"

    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    address = address_from_public_key(pubkey, HRP)
    if msg.show_display:
        title = paths.address_n_to_str(msg.address_n)
        await show_address(ctx, address=address, title=title)

    return BinanceAddress(address=address)
