from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import NostrGetPubkey, NostrPubkey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_pubkey(msg: NostrGetPubkey, keychain: Keychain) -> NostrPubkey:
    from trezor.messages import NostrPubkey

    address_n = msg.address_n

    node = keychain.derive(address_n)
    pk = node.public_key()[-32:]

    return NostrPubkey(pubkey=pk)
