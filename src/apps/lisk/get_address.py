from trezor.messages.LiskAddress import LiskAddress

from .helpers import LISK_CURVE, get_address_from_public_key

from apps.common import seed
from apps.common.display_address import show_address, show_qr


async def layout_lisk_get_address(ctx, msg):
    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker
    address = get_address_from_public_key(pubkey)

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address):
                break

    return LiskAddress(address=address)
