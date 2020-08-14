from trezor.messages.LiskPublicKey import LiskPublicKey

from apps.common import layout, paths
from apps.common.keychain import auto_keychain


@auto_keychain(__name__)
async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return LiskPublicKey(public_key=pubkey)
