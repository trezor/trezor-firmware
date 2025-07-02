from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import StellarSignedTx, StellarSignTx

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def sign_tx(msg: StellarSignTx, keychain: Keychain) -> StellarSignedTx:
    from ubinascii import hexlify

    from trezor import TR
    from trezor.crypto.curve import ed25519
    from trezor.crypto.hashlib import sha256
    from trezor.enums import StellarMemoType
    from trezor.messages import (
        StellarAccountMergeOp,
        StellarCreateAccountOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSignedTx,
        StellarTxOpRequest,
    )
    from trezor.ui.layouts import show_continue_in_app
    from trezor.wire import DataError, ProcessError
    from trezor.wire.context import call_any

    from apps.common import paths, seed

    from . import consts, helpers, layout, writers
    from .operations import process_operation

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())
    num_operations = msg.num_operations  # local_cache_attribute

    if num_operations == 0:
        raise ProcessError("Stellar: At least one operation is required")

    w = bytearray()

    # ---------------------------------
    # INIT
    # ---------------------------------
    is_sending_from_trezor_account = True
    current_output_index = 0

    network_passphrase_hash = sha256(msg.network_passphrase.encode()).digest()
    writers.write_bytes_fixed(w, network_passphrase_hash, 32)
    writers.write_bytes_fixed(w, consts.TX_TYPE, 4)

    address = helpers.address_from_public_key(pubkey)
    accounts_match = msg.source_account == address

    writers.write_pubkey(w, msg.source_account)
    writers.write_uint32(w, msg.fee)
    writers.write_uint64(w, msg.sequence_number)

    if not accounts_match:
        is_sending_from_trezor_account = False
        # If the tx source account does not match the Trezor account, we need to confirm it.
        await layout.require_confirm_tx_source(msg.source_account)

    # timebounds are sent as uint32s since that's all we can display, but they must be hashed as 64bit
    writers.write_bool(w, True)
    writers.write_uint64(w, msg.timebounds_start)
    writers.write_uint64(w, msg.timebounds_end)
    memo_type = msg.memo_type  # local_cache_attribute
    memo_text = msg.memo_text  # local_cache_attribute

    writers.write_uint32(w, memo_type)
    if memo_type == StellarMemoType.NONE:
        # nothing is serialized
        memo_confirm_text = ""
    elif memo_type == StellarMemoType.TEXT:
        # Text: 4 bytes (size) + up to 28 bytes
        if memo_text is None:
            raise DataError("Stellar: Missing memo text")
        if len(memo_text) > 28:
            raise ProcessError("Stellar: max length of a memo text is 28 bytes")
        writers.write_string(w, memo_text)
        memo_confirm_text = memo_text
    elif memo_type == StellarMemoType.ID:
        # ID: 64 bit unsigned integer
        if msg.memo_id is None:
            raise DataError("Stellar: Missing memo id")
        writers.write_uint64(w, msg.memo_id)
        memo_confirm_text = str(msg.memo_id)
    elif memo_type in (StellarMemoType.HASH, StellarMemoType.RETURN):
        # Hash/Return: 32 byte hash
        if msg.memo_hash is None:
            raise DataError("Stellar: Missing memo hash")
        writers.write_bytes_fixed(w, bytearray(msg.memo_hash), 32)
        memo_confirm_text = hexlify(msg.memo_hash).decode()
    else:
        raise ProcessError("Stellar invalid memo type")
    await layout.require_confirm_memo(memo_type, memo_confirm_text)

    # ---------------------------------
    # OPERATION
    # ---------------------------------
    writers.write_uint32(w, num_operations)
    for _ in range(num_operations):
        op = await call_any(StellarTxOpRequest(), *consts.op_codes.keys())
        await process_operation(w, op, current_output_index)  # type: ignore [Argument of type "MessageType" cannot be assigned to parameter "op" of type "StellarMessageType" in function "process_operation"]

        if op.source_account is not None and op.source_account != address:  # type: ignore [Cannot access attribute "source_account" for class "MessageType"]
            # if the operation source account does not match the Trezor account
            is_sending_from_trezor_account = False

        if any(
            op_type.is_type_of(op)
            for op_type in [
                StellarAccountMergeOp,
                StellarCreateAccountOp,
                StellarPaymentOp,
                StellarPathPaymentStrictSendOp,
                StellarPathPaymentStrictReceiveOp,
            ]
        ):
            current_output_index += 1

    # ---------------------------------
    # FINAL
    # ---------------------------------
    # 4 null bytes representing a (currently unused) empty union
    writers.write_uint32(w, 0)
    # final confirm
    await layout.require_confirm_final(
        msg.address_n,
        msg.fee,
        (msg.timebounds_start, msg.timebounds_end),
        is_sending_from_trezor_account,
    )

    # sign
    digest = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), digest)
    show_continue_in_app(TR.send__transaction_signed)

    # Add the public key for verification that the right account was used for signing
    return StellarSignedTx(public_key=pubkey, signature=signature)
