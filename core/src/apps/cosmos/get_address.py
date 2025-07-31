from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import CosmosAddress, CosmosGetAddress

    from apps.common.keychain import Keychain

@auto_keychain(__name__)
async def get_address(
    msg: CosmosGetAddress, keychain: Keychain
) -> CosmosAddress:
    from trezor.messages import CosmosAddress
    from apps.common import paths
    from .addr import derive_addr

    address_n = msg.address_n

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)

    address = derive_addr(node.public_key(), msg.prefix)

    if msg.show_display:
        from trezor import TR
        from trezor.ui.layouts import show_address

        await show_address(address)

    return CosmosAddress(address=address)
