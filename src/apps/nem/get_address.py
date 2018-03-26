from apps.wallet.get_address import _show_address
from apps.common import seed
from trezor.messages.NEMAddress import NEMAddress
from .validators import *


async def nem_get_address(ctx, msg):
    network = validate_network(msg.network)
    node = await seed.derive_node(ctx, msg.address_n, NEM_CURVE)
    address = node.nem_address(network)

    if msg.show_display:
        while True:
            if await _show_address(ctx, address):
                break

    return NEMAddress(address=address)
