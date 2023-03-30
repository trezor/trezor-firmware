from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import BinanceGetPublicKey, BinancePublicKey
    from trezor.wire import Context
    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_public_key(
    ctx: Context, msg: BinanceGetPublicKey, keychain: Keychain
) -> BinancePublicKey:
    from ubinascii import hexlify

    from trezor.messages import BinancePublicKey
    from trezor.ui.layouts import show_pubkey

    from apps.common import paths

    await paths.validate_path(ctx, keychain, msg.address_n)
    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()

    if msg.show_display:
        await show_pubkey(ctx, hexlify(pubkey).decode())

    return BinancePublicKey(public_key=pubkey)
