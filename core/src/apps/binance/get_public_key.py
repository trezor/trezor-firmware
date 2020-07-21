from trezor.messages.BinanceGetPublicKey import BinanceGetPublicKey
from trezor.messages.BinancePublicKey import BinancePublicKey

from apps.binance import CURVE, SLIP44_ID, helpers
from apps.common import layout, paths
from apps.common.keychain import Keychain, with_slip44_keychain


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def get_public_key(ctx, msg: BinanceGetPublicKey, keychain: Keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )
    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return BinancePublicKey(pubkey)
