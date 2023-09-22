from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import BinanceAddress, BinanceGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(msg: BinanceGetAddress, keychain: Keychain) -> BinanceAddress:
    from trezor.messages import BinanceAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths

    from .helpers import address_from_public_key

    HRP = "bnb"
    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)
    pubkey = node.public_key()
    address = address_from_public_key(pubkey, HRP)
    if msg.show_display:
        from . import PATTERN, SLIP44_ID

        await show_address(
            address,
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name("BNB", address_n, PATTERN, SLIP44_ID),
            chunkify=bool(msg.chunkify),
        )

    return BinanceAddress(address=address)
