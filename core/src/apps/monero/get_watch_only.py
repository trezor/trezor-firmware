from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import MoneroGetWatchKey, MoneroWatchKey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_watch_only(
    ctx: Context, msg: MoneroGetWatchKey, keychain: Keychain
) -> MoneroWatchKey:
    from apps.common import paths
    from apps.monero import layout, misc
    from apps.monero.xmr import crypto_helpers
    from trezor.messages import MoneroWatchKey

    await paths.validate_path(ctx, keychain, msg.address_n)

    await layout.require_confirm_watchkey(ctx)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)
    address = creds.address
    watch_key = crypto_helpers.encodeint(creds.view_key_private)

    return MoneroWatchKey(watch_key=watch_key, address=address.encode())
