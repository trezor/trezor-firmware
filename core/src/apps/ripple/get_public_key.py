from trezor.messages.RippleGetPublicKey import RippleGetPublicKey
from trezor.messages.RipplePublicKey import RipplePublicKey

from apps.common import paths
from apps.ripple import CURVE, helpers
from apps.ripple.layout import require_get_public_key


async def get_public_key(ctx, msg: RippleGetPublicKey, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    pubkey_str = helpers.bytes_to_hex(pubkey).upper()

    if msg.show_display:
        await require_get_public_key(ctx, pubkey_str)

    return RipplePublicKey(pubkey_str)
