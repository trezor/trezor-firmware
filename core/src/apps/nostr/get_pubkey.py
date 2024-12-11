from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain
from apps.common.signverify import decode_message

if TYPE_CHECKING:
    from trezor.messages import NostrGetPubkey, NostrPubkey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_pubkey(msg: NostrGetPubkey, keychain: Keychain) -> NostrPubkey:
    from ubinascii import hexlify
    from trezor.messages import NostrPubkey

    address_n = msg.address_n
    show_display = msg.show_display

    node = keychain.derive(address_n)
    pk = node.public_key()[-32:]

    if show_display:
        from trezor.ui.layouts import show_pubkey

        await show_pubkey(
            decode_message(hexlify(pk)),
            title="npub",
            account=None,
            path=None,
            mismatch_title="npub mismatch?",
            br_name="show_npub",
        )

    return NostrPubkey(pubkey=pk)
