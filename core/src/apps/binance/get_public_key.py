from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import BinanceGetPublicKey, BinancePublicKey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_public_key(
    msg: BinanceGetPublicKey, keychain: Keychain
) -> BinancePublicKey | None:
    from ubinascii import hexlify

    from trezor.messages import BinancePublicKey
    from trezor.ui.layouts import show_continue_in_app, show_pubkey
    from trezor.wire import context

    from apps.common import paths

    await paths.validate_path(keychain, msg.address_n)
    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    response = BinancePublicKey(public_key=pubkey)

    if msg.show_display:
        from trezor import TR

        from . import PATTERN, SLIP44_ID

        path = paths.address_n_to_str(msg.address_n)
        await show_pubkey(
            hexlify(pubkey).decode(),
            account=paths.get_account_name("BNB", msg.address_n, PATTERN, SLIP44_ID),
            path=path,
        )
        await context.write(response)
        await show_continue_in_app(TR.address__public_key_confirmed)
        return None

    return response
