from trezor.messages.BinanceGetPublicKey import BinanceGetPublicKey
from trezor.messages.BinancePublicKey import BinancePublicKey

from apps.binance import CURVE, helpers
from apps.common import layout, paths


async def get_public_key(ctx, msg: BinanceGetPublicKey, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )
    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return BinancePublicKey(pubkey)
