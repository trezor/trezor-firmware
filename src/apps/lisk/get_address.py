from apps.wallet.get_address import _show_address, _show_qr
from .helpers import LISK_CURVE, get_address_from_public_key


async def layout_lisk_get_address(ctx, msg):
    from trezor.messages.LiskAddress import LiskAddress
    from ..common import seed

    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker
    address = get_address_from_public_key(pubkey)

    if msg.show_display:
        while True:
            if await _show_address(ctx, address):
                break
            if await _show_qr(ctx, address):
                break

    return LiskAddress(address=address)
