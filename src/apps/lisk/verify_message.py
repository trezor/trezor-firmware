
async def lisk_verify_message(ctx, msg):
    from trezor.crypto.curve import ed25519
    from .helpers import get_address_from_public_key
    from trezor import wire
    from trezor.messages.Success import Success
    from trezor.messages.FailureType import ProcessError
    from apps.wallet.verify_message import require_confirm_verify_message

    # Lisk signature can be more than 64 bytes
    sig = msg.signature[:64]
    verify = ed25519.verify(msg.public_key, sig, msg.message)

    if not verify:
        raise wire.FailureError(ProcessError, 'Invalid signature')

    address = get_address_from_public_key(msg.public_key)

    await require_confirm_verify_message(ctx, address, msg.message)

    return Success(message='Message verified')
