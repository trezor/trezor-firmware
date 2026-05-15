from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import SolanaVerifyMessage, Success


async def verify_message(msg: SolanaVerifyMessage) -> Success:
    from trezor import TR
    from trezor.messages import Success
    from trezor.ui.layouts import show_success

    from .layout import confirm_offchain_signverify
    from .offchain_message import Envelope

    envelope = Envelope.from_bytes(msg.envelope)

    envelope.verify()

    await confirm_offchain_signverify(
        envelope.message, verify=True, chunkify=bool(msg.chunkify)
    )

    # TODO: add a generic (not specific to any coin) valid signature message
    await show_success("verify_message", TR.ethereum__valid_signature)
    return Success(message="Signature ok")
