"""Verify a CKB signed message."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import CKBVerifyMessage, Success


async def verify_message(msg: CKBVerifyMessage) -> Success:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_signverify, show_success
    from trezor.wire import DataError, ProcessError

    from apps.common.signverify import decode_message

    from .helpers import encode_address, get_lock_script_arg, message_digest

    address = msg.address
    signature = msg.signature
    message = msg.message
    network = msg.network

    if network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")

    if len(signature) != 65:
        raise DataError("Invalid signature length")

    digest = message_digest(message)

    # Convert CKB native format [R(32) | S(32) | recovery_id(1)] to internal
    # verify_recover needs compressed flag (31 + recid) to return compressed pubkey
    recid = signature[64]
    if recid > 3:
        raise DataError("Invalid recovery ID")
    internal_sig = bytes([recid + 31]) + signature[:64]
    pubkey = secp256k1.verify_recover(internal_sig, digest)
    if not pubkey:
        raise ProcessError("Invalid signature")

    arg = get_lock_script_arg(pubkey)
    recovered_address = encode_address(arg, network)

    if recovered_address != address:
        raise ProcessError("Invalid signature")

    await confirm_signverify(
        decode_message(message),
        address,
        verify=True,
        chunkify=bool(msg.chunkify),
    )

    await show_success("verify_message", TR.bitcoin__valid_signature)
    return Success(message="Message verified")
