from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import NostrGetPubkey, NostrPubkey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_pubkey(msg: NostrGetPubkey, keychain: Keychain) -> NostrPubkey:
    from trezor.messages import NostrPubkey

    from apps.common import paths

    address_n = msg.address_n

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)
    pk = node.public_key()[-32:]

    if msg.show_display:
        from trezor.ui.layouts import show_pubkey

        from apps.common.contacts import encode_npub

        await show_pubkey(
            encode_npub(pk),
            "Nostr public key",
            path=paths.address_n_to_str(address_n),
        )

    return NostrPubkey(pubkey=pk)
