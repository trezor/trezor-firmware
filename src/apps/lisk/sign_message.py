from apps.common import seed
from apps.common.confirm import require_confirm
from apps.common.signverify import split_message
from apps.wallet.sign_tx.signing import write_varint
from trezor import ui
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages.LiskMessageSignature import LiskMessageSignature
from trezor.ui.text import Text
from trezor.utils import HashWriter

from .helpers import LISK_CURVE


def message_digest(message):
    h = HashWriter(sha256)
    signed_message_header = 'Lisk Signed Message:\n'
    write_varint(h, len(signed_message_header))
    h.extend(signed_message_header)
    write_varint(h, len(message))
    h.extend(message)
    return sha256(h.get_digest()).digest()


async def lisk_sign_message(ctx, msg):
    message = msg.message
    address_n = msg.address_n or ()

    await require_confirm_sign_message(ctx, message)

    node = await seed.derive_node(ctx, address_n, LISK_CURVE)
    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    signature = ed25519.sign(seckey, message_digest(message))

    return LiskMessageSignature(public_key=pubkey, signature=signature)


async def require_confirm_sign_message(ctx, message):
    message = split_message(message)
    content = Text('Sign Lisk message', ui.ICON_DEFAULT, max_lines=5, *message)
    await require_confirm(ctx, content)
