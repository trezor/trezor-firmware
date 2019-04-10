from trezor.messages.MoneroGetWatchKey import MoneroGetWatchKey
from trezor.messages.MoneroWatchKey import MoneroWatchKey

from apps.common import paths
from apps.monero import CURVE, misc
from apps.monero.layout import confirms
from apps.monero.xmr import crypto


async def get_watch_only(ctx, msg: MoneroGetWatchKey, keychain):
    await paths.validate_path(
        ctx, misc.validate_full_path, keychain, msg.address_n, CURVE
    )

    await confirms.require_confirm_watchkey(ctx)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)
    address = creds.address
    watch_key = crypto.encodeint(creds.view_key_private)

    return MoneroWatchKey(watch_key=watch_key, address=address)
