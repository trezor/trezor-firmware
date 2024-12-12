from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import NostrEventSignature, NostrSignEvent

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def sign_event(msg: NostrSignEvent, keychain: Keychain) -> NostrEventSignature:
    from ubinascii import hexlify

    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.messages import NostrEventSignature
    from trezor.ui.layouts import confirm_action, confirm_new_contact

    address_n = msg.address_n
    created_at = msg.created_at
    kind = msg.kind
    tags = msg.tags
    content = msg.content

    if content and kind == 27922:
        if "/" not in content:
            raise ValueError("Invalid content")
        # message will have format <label>/<npub>
        # hackathon simplification
        label, contact_id = content.split("/")
        await confirm_new_contact(
            label=label,
            contact_id=contact_id,
            chunkify=True,
        )
    else:
        await confirm_action(
            "nostr_sign_event", "Nostr event", action="Sign nostr event", description=""
        )

    node = keychain.derive(address_n)
    # pk = node.public_key()[-32:]
    pk = node.public_key()
    sk = node.private_key()

    serialized_event = (
        f'[0,"{hexlify(pk).decode()}",{created_at},{kind},{tags},"{content}"]'
    )
    print("serialized_event", serialized_event)
    event_id = sha256(serialized_event).digest()
    # signature = secp256k1.sign(sk, event_id)[-64:]
    signature = secp256k1.sign(sk, event_id)

    return NostrEventSignature(pubkey=pk, id=event_id, signature=signature)
