from trezor import wire
from trezor.crypto.curve import ed25519
from trezor.messages import Success
from trezor.ui.layouts import confirm_signverify

from apps.common.signverify import decode_message

from .helpers import get_address_from_public_key
from .sign_message import message_digest


async def verify_message(ctx, msg):
    digest = message_digest(msg.message)
    verified = ed25519.verify(msg.public_key, msg.signature, digest)
    if not verified:
        raise wire.ProcessError("Invalid signature")

    address = get_address_from_public_key(msg.public_key)
    await confirm_signverify(ctx, "Lisk", decode_message(msg.message), address=address)

    return Success(message="Message verified")
