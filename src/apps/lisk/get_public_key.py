from apps.wallet.get_public_key import _show_pubkey
from .helpers import LISK_CURVE


async def lisk_get_public_key(ctx, msg):
    from trezor.messages.LiskPublicKey import LiskPublicKey
    from trezor.crypto.curve import ed25519
    from ..common import seed

    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)

    seckey = node.private_key()
    public_key = ed25519.publickey(seckey)

    if msg.show_display:
        await _show_pubkey(ctx, public_key)

    return LiskPublicKey(public_key=public_key)
