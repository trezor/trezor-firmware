from typing import TYPE_CHECKING

from trezor.messages import EthereumAddress

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumGetAddress, EthereumAddress, EthereumNetworkInfo
    from trezor.wire import Context

    from apps.common.keychain import Keychain


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def get_address(
    ctx: Context,
    msg: EthereumGetAddress,
    keychain: Keychain,
    network: EthereumNetworkInfo,
) -> EthereumAddress:
    from trezor.messages import EthereumAddress
    from trezor.ui.layouts import show_address
    from apps.common import paths
    from . import networks
    from .helpers import address_from_bytes

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(ctx, keychain, address_n)

    node = keychain.derive(address_n)

    if len(msg.address_n) > 1:  # path has slip44 network identifier
        slip44 = msg.address_n[1] & 0x7FFF_FFFF
        if network is not networks.UNKNOWN_NETWORK and slip44 == network.slip44:
            network_to_use = network
        else:
            network_to_use = networks.by_slip44(slip44) or networks.UNKNOWN_NETWORK
    else:
        network_to_use = networks.UNKNOWN_NETWORK
    address = address_from_bytes(node.ethereum_pubkeyhash(), network_to_use)

    if msg.show_display:
        title = paths.address_n_to_str(address_n)
        await show_address(ctx, address, title=title)

    return EthereumAddress(address=address)
