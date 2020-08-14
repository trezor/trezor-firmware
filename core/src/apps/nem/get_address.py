from trezor.messages.NEMAddress import NEMAddress

from apps.common.keychain import with_slip44_keychain
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.common.paths import validate_path

from . import CURVE, PATTERNS, SLIP44_ID
from .helpers import check_path, get_network_str
from .validators import validate_network


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(ctx, msg, keychain):
    network = validate_network(msg.network)
    await validate_path(
        ctx, keychain, msg.address_n, check_path(msg.address_n, msg.network)
    )

    node = keychain.derive(msg.address_n)
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
