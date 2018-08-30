from ubinascii import hexlify

from trezor import log, ui, wire
from trezor.crypto.curve import ed25519
from trezor.messages.Failure import Failure
from trezor.messages.Success import Success

from .address import validate_full_path
from .layout import confirm_with_pagination

from apps.common import paths


async def verify_message(ctx, msg):
    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)

    try:
        res = _verify_message(msg.public_key, msg.signature, msg.message)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Verifying failed")

    if not res:
        return Failure(message="Invalid signature")

    if not await confirm_with_pagination(
        ctx, msg.message, "Verifying message", ui.ICON_RECEIVE, ui.GREEN
    ):
        raise wire.ActionCancelled("Verifying cancelled")

    if not await confirm_with_pagination(
        ctx, hexlify(msg.public_key), "With public key", ui.ICON_RECEIVE, ui.GREEN
    ):
        raise wire.ActionCancelled("Verifying cancelled")

    return Success(message="Message verified")


def _verify_message(public_key: bytes, signature: bytes, message: str):
    return ed25519.verify(public_key, signature, message)
