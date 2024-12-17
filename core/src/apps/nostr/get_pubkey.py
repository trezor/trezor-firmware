from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain
from apps.common.signverify import decode_message

from trezor import TR

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
        from trezor.ui.layouts import show_address

        await show_address(
            decode_message(hexlify(pk)),
            title=TR.nostr__public_key,
            br_name="nostr_show_pubkey",
        )

    return NostrPubkey(pubkey=pk)
