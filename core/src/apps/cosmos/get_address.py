from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import CosmosAddress, CosmosGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(msg: CosmosGetAddress, keychain: Keychain) -> CosmosAddress:
    """
    Get a Cosmos address for the requested derivation path and prefix.

    Args:
        msg: Request containing the derivation path and bech32 prefix.
        keychain: Keychain used to derive the requested node.

    Returns:
        Cosmos address encoded with the requested bech32 prefix.
    """
    from trezor import wire
    from trezor.messages import CosmosAddress

    from apps.common import paths

    from . import SUPPORTED_ADDRESS_PREFIXES
    from .addr import derive_addr

    address_n = msg.address_n

    if msg.prefix not in SUPPORTED_ADDRESS_PREFIXES:
        raise wire.DataError("Unsupported address prefix")

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)

    address = derive_addr(node.public_key(), msg.prefix)

    if msg.show_display:
        from trezor.ui.layouts import show_address

        await show_address(address)

    return CosmosAddress(address=address)
