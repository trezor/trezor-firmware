from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages.LiskMessageSignature import LiskMessageSignature
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.keychain import with_slip44_keychain
from apps.common.signverify import require_confirm_sign_message
from apps.common.writers import write_bitcoin_varint
from apps.lisk import CURVE, SLIP44_ID
from apps.lisk.helpers import validate_full_path


def message_digest(message):
    h = HashWriter(sha256())
    signed_message_header = "Lisk Signed Message:\n"
    write_bitcoin_varint(h, len(signed_message_header))
    h.extend(signed_message_header)
    write_bitcoin_varint(h, len(message))
    h.extend(message)
    return sha256(h.get_digest()).digest()


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def sign_message(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)
    await require_confirm_sign_message(ctx, "Lisk", msg.message)

    node = keychain.derive(msg.address_n)
    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    signature = ed25519.sign(seckey, message_digest(msg.message))

    return LiskMessageSignature(public_key=pubkey, signature=signature)
