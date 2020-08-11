from trezor import wire
from trezor.crypto.curve import ed25519
from trezor.messages.Success import Success

from apps.common.signverify import require_confirm_verify_message

from .helpers import get_address_from_public_key
from .sign_message import message_digest


async def verify_message(ctx, msg):
    digest = message_digest(msg.message)
    verified = ed25519.verify(msg.public_key, msg.signature, digest)
    if not verified:
        raise wire.ProcessError("Invalid signature")

    address = get_address_from_public_key(msg.public_key)
    await require_confirm_verify_message(ctx, address, "Lisk", msg.message)

    return Success(message="Message verified")
