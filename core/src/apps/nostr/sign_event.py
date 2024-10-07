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

    from apps.common import paths

    address_n = msg.address_n
    created_at = msg.created_at
    kind = msg.kind
    tags = [[t.key] + ([t.value] if t.value else []) + t.extra for t in msg.tags]
    content = msg.content

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)
    pk = node.public_key()[-32:]

    # The event ID is obtained by serializing the event in a specific way:
    # "[0,pubkey,created_at,kind,tags,content]"
    # See NIP-01: https://github.com/nostr-protocol/nips/blob/master/01.md
    serialized_tags = ",".join(
        ["[" + ",".join(f'"{t}"' for t in tag) + "]" for tag in tags]
    )
    serialized_event = f'[0,"{hexlify(pk).decode()}",{created_at},{kind},[{serialized_tags}],"{content}"]'
    event_id = sha256(serialized_event).digest()

    # The event signature is basically the signature of the event ID computed above
    signature = secp256k1.sign(sk, event_id)[-64:]

    return NostrEventSignature(
        pubkey=pk,
        id=event_id,
        signature=signature,
    )
