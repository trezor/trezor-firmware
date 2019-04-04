from trezor.messages.LiskPublicKey import LiskPublicKey

from .helpers import LISK_CURVE, validate_full_path

from apps.common import layout, paths


async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n)

    node = keychain.derive(msg.address_n, LISK_CURVE)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return LiskPublicKey(public_key=pubkey)
