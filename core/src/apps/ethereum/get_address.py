from typing import TYPE_CHECKING

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from apps.common.keychain import Keychain
    from trezor.messages import EthereumAddress, EthereumGetAddress
    from trezor.wire import Context


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def get_address(
    ctx: Context, msg: EthereumGetAddress, keychain: Keychain
) -> EthereumAddress:
    from apps.common import paths
    from trezor.messages import EthereumAddress
    from trezor.ui.layouts import show_address

    from . import networks
    from .helpers import address_from_bytes

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(ctx, keychain, address_n)

    node = keychain.derive(address_n)

    if len(address_n) > 1:  # path has slip44 network identifier
        network = networks.by_slip44(address_n[1] & 0x7FFF_FFFF)
    else:
        network = None
    address = address_from_bytes(node.ethereum_pubkeyhash(), network)

    if msg.show_display:
        await show_address(ctx, address, path=paths.address_n_to_str(address_n))

    return EthereumAddress(address=address)
