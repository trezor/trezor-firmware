from trezor import wire
from trezor.crypto.curve import ed25519
from trezor.messages.Success import Success
from trezor.wire import errors

from .helpers import get_address_from_public_key
from .sign_message import message_digest

from apps.wallet.verify_message import require_confirm_verify_message


async def verify_message(ctx, msg):
    digest = message_digest(msg.message)
    verified = ed25519.verify(msg.public_key, msg.signature, digest)
    if not verified:
        raise errors.ProcessError("Invalid signature")

    address = get_address_from_public_key(msg.public_key)
    await require_confirm_verify_message(ctx, address, msg.message)

    return Success(message="Message verified")
