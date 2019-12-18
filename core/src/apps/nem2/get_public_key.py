from trezor.messages.NEM2GetPublicKey import NEM2GetPublicKey
from trezor.messages.NEM2PublicKey import NEM2PublicKey

from apps.common import seed
from apps.common.layout import show_pubkey
from apps.common.paths import validate_path
from apps.nem2 import CURVE
from apps.nem2.helpers import validate_nem2_path

async def get_public_key(ctx, msg:NEM2GetPublicKey, keychain):
    await validate_path(ctx, validate_nem2_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n, CURVE)
    pubkey = seed.remove_ed25519_prefix(node.public_key())

    if msg.show_display:
        await show_pubkey(ctx, pubkey)

    return NEM2PublicKey(pubkey)
