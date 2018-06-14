from ubinascii import hexlify

from trezor import log, ui, wire
from trezor.crypto.curve import ed25519
from trezor.messages.Failure import Failure
from trezor.messages.Success import Success

from .ui import show_swipable_with_confirmation


async def cardano_verify_message(ctx, msg):
    try:
        res = _verify_message(msg.public_key, msg.signature, msg.message)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Verifying failed")

    if not res:
        return Failure(message="Invalid signature")

    if not await show_swipable_with_confirmation(
        ctx, msg.message, "Verifying message", ui.ICON_RECEIVE, ui.GREEN
    ):
        raise wire.ActionCancelled("Verifying cancelled")

    if not await show_swipable_with_confirmation(
        ctx, hexlify(msg.public_key), "With public key", ui.ICON_RECEIVE, ui.GREEN
    ):
        raise wire.ActionCancelled("Verifying cancelled")

    return Success(message="Message verified")


def _verify_message(public_key: bytes, signature: bytes, message: str):
    return ed25519.verify(public_key, signature, message)
