from trezor.messages.NEMAddress import NEMAddress

from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.common.paths import validate_path
from apps.nem import CURVE
from apps.nem.helpers import check_path, get_network_str
from apps.nem.validators import validate_network


async def get_address(ctx, msg, keychain):
    network = validate_network(msg.network)
    await validate_path(
        ctx, check_path, keychain, msg.address_n, CURVE, network=network
    )

    node = keychain.derive(msg.address_n, CURVE)
    address = node.nem_address(network)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(
                ctx, address, desc=desc, network=get_network_str(network)
            ):
                break
            if await show_qr(ctx, address.upper(), desc=desc):
                break

    return NEMAddress(address=address)
