from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import SolanaVerifyMessage, Success


async def verify_message(msg: SolanaVerifyMessage) -> Success:
    from trezor import TR
    from trezor.crypto.curve import ed25519
    from trezor.messages import Success
    from trezor.ui.layouts import show_success
    from trezor.wire import DataError

    from .layout import confirm_offchain_signverify
    from .offchain_message import serialize_offchain_message

    serialized = serialize_offchain_message(msg.message)

    if len(msg.signatures) != len(msg.message.signers):
        raise DataError("Number of signatures must match number of signers")
    for signature, signer in zip(msg.signatures, msg.message.signers):
        if not ed25519.verify(signer, signature, serialized):
            raise DataError("Invalid signature")

    await confirm_offchain_signverify(
        msg.message, verify=True, chunkify=bool(msg.chunkify)
    )

    # TODO: add a generic (not specific to any coin) valid signature message
    await show_success("verify_message", TR.ethereum__valid_signature)
    return Success(message="Signature ok")
