from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages.LiskMessageSignature import LiskMessageSignature
from trezor.ui.text import Text
from trezor.utils import HashWriter

from .helpers import LISK_CURVE, validate_full_path

from apps.common import paths, seed
from apps.common.confirm import require_confirm
from apps.common.signverify import split_message
from apps.wallet.sign_tx.signing import write_varint


def message_digest(message):
    h = HashWriter(sha256())
    signed_message_header = "Lisk Signed Message:\n"
    write_varint(h, len(signed_message_header))
    h.extend(signed_message_header)
    write_varint(h, len(message))
    h.extend(message)
    return sha256(h.get_digest()).digest()


async def sign_message(ctx, msg):
    keychain = await seed.get_keychain(ctx)

    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)
    await require_confirm_sign_message(ctx, msg.message)

    node = keychain.derive(msg.address_n, LISK_CURVE)
    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    signature = ed25519.sign(seckey, message_digest(msg.message))

    return LiskMessageSignature(public_key=pubkey, signature=signature)


async def require_confirm_sign_message(ctx, message):
    message = split_message(message)
    text = Text("Sign Lisk message", new_lines=False)
    text.normal(*message)
    await require_confirm(ctx, text)
