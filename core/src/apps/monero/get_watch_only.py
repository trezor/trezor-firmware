from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import MoneroGetWatchKey, MoneroWatchKey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_watch_only(msg: MoneroGetWatchKey, keychain: Keychain) -> MoneroWatchKey:
    from trezor.messages import MoneroWatchKey

    from apps.common import paths
    from apps.monero import layout
    from apps.monero.xmr import addresses, crypto
    from apps.monero.xmr.networks import net_version

    await paths.validate_path(keychain, msg.address_n)

    await layout.require_confirm_watchkey()

    node = keychain.derive(msg.address_n)
    public_spend, public_view, watch_key = crypto.wallet_public(node, 0, 0, True)
    assert watch_key is not None
    address = addresses.encode_addr(
        net_version(msg.network_type), public_spend, public_view
    )

    return MoneroWatchKey(watch_key=watch_key, address=address.encode())
