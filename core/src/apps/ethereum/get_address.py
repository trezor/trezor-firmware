from typing import TYPE_CHECKING

from trezor.messages import EthereumAddress
from trezor.ui.layouts import show_address

from apps.common import paths

from . import networks
from .helpers import address_from_bytes
from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumGetAddress, EthereumAddress
    from trezor.wire import Context

    from apps.common.keychain import Keychain

    from . import definitions


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def get_address(
    ctx: Context,
    msg: EthereumGetAddress,
    keychain: Keychain,
    defs: definitions.Definitions,
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
        if defs.network is not None and slip44 == defs.network.slip44:
            network = defs.network
        else:
            network = networks.by_slip44(slip44) or networks.UNKNOWN_NETWORK
    else:
        network = networks.UNKNOWN_NETWORK
    address = address_from_bytes(node.ethereum_pubkeyhash(), network)

    if msg.show_display:
        title = paths.address_n_to_str(address_n)
        await show_address(ctx, address, title=title)

    return EthereumAddress(address=address)
