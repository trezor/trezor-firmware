from trezor.messages.LiskPublicKey import LiskPublicKey

from apps.common import layout, paths
from apps.lisk import CURVE
from apps.lisk.helpers import validate_full_path


async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n, CURVE)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return LiskPublicKey(public_key=pubkey)
