from typing import TYPE_CHECKING

from trezor.messages import EthereumAddress

from .keychain import PATTERNS_ADDRESS, with_keychain_and_network_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumGetAddress, EthereumAddress, EthereumNetworkInfo
    from trezor.wire import Context

    from apps.common.keychain import Keychain


@with_keychain_and_network_from_path(*PATTERNS_ADDRESS)
async def get_address(
    ctx: Context,
    msg: EthereumGetAddress,
    keychain: Keychain,
    network: EthereumNetworkInfo,
) -> EthereumAddress:
    from trezor.messages import EthereumAddress
    from trezor.ui.layouts import show_address
    from apps.common import paths
    from .helpers import address_from_bytes

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(ctx, keychain, address_n)

    node = keychain.derive(address_n)

    address = address_from_bytes(node.ethereum_pubkeyhash(), network)

    if msg.show_display:
        title = paths.address_n_to_str(address_n)
        await show_address(ctx, address, title=title)

    return EthereumAddress(address=address)
