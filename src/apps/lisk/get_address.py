from apps.wallet.get_address import _show_address, _show_qr
from .helpers import LISK_CURVE, get_address_from_public_key


async def layout_lisk_get_address(ctx, msg):
    from trezor.messages.LiskAddress import LiskAddress
    from trezor.crypto.curve import ed25519
    from ..common import seed

    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)

    seckey = node.private_key()
    public_key = ed25519.publickey(seckey)
    address = get_address_from_public_key(public_key)

    if msg.show_display:
        while True:
            if await _show_address(ctx, address):
                break
            if await _show_qr(ctx, address):
                break

    return LiskAddress(address=address)
