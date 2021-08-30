from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages import LiskMessageSignature
from trezor.ui.layouts import confirm_signverify
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.common.signverify import decode_message
from apps.common.writers import write_bitcoin_varint

from .helpers import get_address_from_public_key


def message_digest(message):
    h = HashWriter(sha256())
    signed_message_header = "Lisk Signed Message:\n"
    write_bitcoin_varint(h, len(signed_message_header))
    h.extend(signed_message_header)
    write_bitcoin_varint(h, len(message))
    h.extend(message)
    return sha256(h.get_digest()).digest()


@auto_keychain(__name__)
async def sign_message(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker
    address = get_address_from_public_key(pubkey)

    await confirm_signverify(ctx, "Lisk", decode_message(msg.message), address)

    seckey = node.private_key()
    signature = ed25519.sign(seckey, message_digest(msg.message))

    return LiskMessageSignature(public_key=pubkey, signature=signature)
