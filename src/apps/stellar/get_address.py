from trezor.messages.StellarAddress import StellarAddress
from trezor.messages.StellarGetAddress import StellarGetAddress

from apps.common import seed
from apps.common.layout import show_address, show_qr
from apps.stellar import helpers


async def get_address(ctx, msg: StellarGetAddress):
    node = await seed.derive_node(ctx, msg.address_n, helpers.STELLAR_CURVE)
    pubkey = seed.remove_ed25519_prefix(node.public_key())
    address = helpers.address_from_public_key(pubkey)

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address.upper()):
                break

    return StellarAddress(address=address)
