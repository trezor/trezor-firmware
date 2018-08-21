from trezor.messages.StellarGetPublicKey import StellarGetPublicKey
from trezor.messages.StellarPublicKey import StellarPublicKey

from apps.common import seed
from apps.common.show import show_pubkey
from apps.stellar import helpers


async def get_public_key(ctx, msg: StellarGetPublicKey):
    node = await seed.derive_node(ctx, msg.address_n, helpers.STELLAR_CURVE)
    pubkey = seed.remove_ed25519_prefix(node.public_key())

    if msg.show_display:
        await show_pubkey(ctx, pubkey)

    return StellarPublicKey(public_key=pubkey)
