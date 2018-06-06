from .helpers import LISK_CURVE, get_address_from_public_key
from apps.wallet.sign_message import require_confirm_sign_message
from trezor.crypto.hashlib import sha256
from trezor.utils import HashWriter
from apps.wallet.sign_tx.signing import write_varint

def message_digest(message):
    h = HashWriter(sha256)
    signed_message_header = 'Lisk Signed Message:\n'
    write_varint(h, len(signed_message_header))
    h.extend(signed_message_header)
    write_varint(h, len(message))
    h.extend(message)
    return sha256(h.get_digest()).digest()


async def lisk_sign_message(ctx, msg):
    from trezor.messages.LiskMessageSignature import LiskMessageSignature
    from trezor.crypto.curve import ed25519
    from ..common import seed

    message = msg.message

    await require_confirm_sign_message(ctx, message)

    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)
    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    signature = ed25519.sign(seckey, message_digest(message))

    return LiskMessageSignature(public_key=pubkey, signature=signature)
