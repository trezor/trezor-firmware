from trezor.messages.LiskPublicKey import LiskPublicKey

from apps.common import layout, paths
from apps.common.keychain import with_slip44_keychain
from apps.lisk import CURVE, SLIP44_ID
from apps.lisk.helpers import validate_full_path


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return LiskPublicKey(public_key=pubkey)
