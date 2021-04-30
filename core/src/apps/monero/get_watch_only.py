from trezor.messages import MoneroGetWatchKey, MoneroWatchKey

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.monero import misc
from apps.monero.layout import confirms
from apps.monero.xmr import crypto


@auto_keychain(__name__)
async def get_watch_only(ctx, msg: MoneroGetWatchKey, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    await confirms.require_confirm_watchkey(ctx)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)
    address = creds.address
    watch_key = crypto.encodeint(creds.view_key_private)

    return MoneroWatchKey(watch_key=watch_key, address=address)
