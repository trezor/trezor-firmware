from trezor.messages.LiskPublicKey import LiskPublicKey

from .helpers import LISK_CURVE

from apps.common import seed
from apps.wallet.get_public_key import _show_pubkey


async def lisk_get_public_key(ctx, msg):
    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    if msg.show_display:
        await _show_pubkey(ctx, pubkey)

    return LiskPublicKey(public_key=pubkey)
