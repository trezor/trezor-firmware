from trezor.messages.RippleAddress import RippleAddress
from trezor.messages.RippleGetAddress import RippleGetAddress

from . import helpers

from apps.common import seed
from apps.common.layout import show_address, show_qr


async def get_address(ctx, msg: RippleGetAddress):
    node = await seed.derive_node(ctx, msg.address_n)
    pubkey = node.public_key()
    address = helpers.address_from_public_key(pubkey)

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address.upper()):
                break

    return RippleAddress(address=address)
