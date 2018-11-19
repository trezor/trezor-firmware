from trezor.messages.RippleAddress import RippleAddress
from trezor.messages.RippleGetAddress import RippleGetAddress

from . import helpers

from apps.common import paths, seed
from apps.common.layout import address_n_to_str, show_address, show_qr


async def get_address(ctx, msg: RippleGetAddress):
    await paths.validate_path(ctx, helpers.validate_full_path, path=msg.address_n)

    node = await seed.derive_node(ctx, msg.address_n)
    pubkey = node.public_key()
    address = helpers.address_from_public_key(pubkey)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address.upper(), desc=desc):
                break

    return RippleAddress(address=address)
