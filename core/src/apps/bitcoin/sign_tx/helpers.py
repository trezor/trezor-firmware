from typing import TYPE_CHECKING

from trezor.enums import InputScriptType, OutputScriptType, RequestType
from trezor.messages import (
    PaymentRequest,
    TxAckInput,
    TxAckOutput,
    TxAckPrevExtraData,
    TxAckPrevInput,
    TxAckPrevMeta,
    TxAckPrevOutput,
)
from trezor.wire import DataError

from .. import common
from ..writers import TX_HASH_SIZE

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any

    from trezor.messages import (
        PrevInput,
        PrevOutput,
        PrevTx,
        SignTx,
        TxInput,
        TxOutput,
        TxRequest,
    )

    from apps.common.coininfo import CoinInfo


async def request_tx_meta(
    tx_req: TxRequest, coin: CoinInfo, tx_hash: AnyBytes | None = None
) -> PrevTx:
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXMETA
    tx_req.details.tx_hash = tx_hash
    ack = await _call_tx_request(tx_req, TxAckPrevMeta)
    return _sanitize_tx_meta(ack.tx, coin)


async def request_tx_extra_data(
    tx_req: TxRequest, offset: int, size: int, tx_hash: AnyBytes | None = None
) -> AnyBytes:
    details = tx_req.details  # local_cache_attribute

    assert details is not None
    tx_req.request_type = RequestType.TXEXTRADATA
    details.extra_data_offset = offset
    details.extra_data_len = size
    details.tx_hash = tx_hash
    ack = await _call_tx_request(tx_req, TxAckPrevExtraData)
    extra_data_chunk = ack.tx.extra_data_chunk
    assert extra_data_chunk is not None
    return extra_data_chunk


async def request_tx_input(
    tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: AnyBytes | None = None
) -> TxInput:
    assert tx_req.details is not None
    if tx_hash:
        tx_req.request_type = RequestType.TXORIGINPUT
        tx_req.details.tx_hash = tx_hash
    else:
        tx_req.request_type = RequestType.TXINPUT
    tx_req.details.request_index = i
    ack = await _call_tx_request(tx_req, TxAckInput)
    return _sanitize_tx_input(ack.tx.input, coin)


async def request_tx_prev_input(
    tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: AnyBytes | None = None
) -> PrevInput:
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = await _call_tx_request(tx_req, TxAckPrevInput)
    return _sanitize_tx_prev_input(ack.tx.input, coin)


async def request_tx_output(
    tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: AnyBytes | None = None
) -> TxOutput:
    assert tx_req.details is not None
    if tx_hash:
        tx_req.request_type = RequestType.TXORIGOUTPUT
        tx_req.details.tx_hash = tx_hash
    else:
        tx_req.request_type = RequestType.TXOUTPUT
    tx_req.details.request_index = i
    ack = await _call_tx_request(tx_req, TxAckOutput)
    return _sanitize_tx_output(ack.tx.output, coin)


async def request_tx_prev_output(
    tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: AnyBytes | None = None
) -> PrevOutput:
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = await _call_tx_request(tx_req, TxAckPrevOutput)
    # return sanitize_tx_prev_output(ack.tx, coin)  # no sanitize is required
    return ack.tx.output


async def request_payment_req(tx_req: TxRequest, i: int) -> PaymentRequest:
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXPAYMENTREQ
    tx_req.details.request_index = i
    return await _call_tx_request(tx_req, PaymentRequest)


def request_tx_finish(tx_req: TxRequest) -> None:
    tx_req.request_type = RequestType.TXFINISHED


async def _call_tx_request(tx_req: TxRequest, expected_type: type[Any]) -> Any:
    from trezor.wire.context import call

    ack = await call(tx_req, expected_type)
    _clear_tx_request(tx_req)
    return ack


def _clear_tx_request(tx_req: TxRequest) -> None:
    details = tx_req.details  # local_cache_attribute
    serialized = tx_req.serialized  # local_cache_attribute

    assert details is not None
    assert serialized is not None
    assert serialized.serialized_tx is not None
    tx_req.request_type = None
    details.request_index = None
    details.tx_hash = None
    details.extra_data_len = None
    details.extra_data_offset = None
    serialized.signature = None
    serialized.signature_index = None
    # typechecker thinks serialized_tx is `bytes`, which is immutable
    # we know that it is `bytearray` in reality
    serialized.serialized_tx[:] = bytes()  # type: ignore ["__setitem__" method not defined on type "bytes"]


# Data sanitizers
# ===


def sanitize_sign_tx(tx: SignTx, coin: CoinInfo) -> SignTx:
    if coin.decred or coin.overwintered:
        tx.expiry = tx.expiry if tx.expiry is not None else 0
    elif tx.expiry:
        raise DataError("Expiry not enabled on this coin.")

    if coin.timestamp and not tx.timestamp:
        raise DataError("Timestamp must be set.")
    elif not coin.timestamp and tx.timestamp:
        raise DataError("Timestamp not enabled on this coin.")

    if coin.overwintered:
        if tx.version_group_id is None:
            raise DataError("Version group ID must be set.")
        if tx.branch_id is None:
            raise DataError("Branch ID must be set.")
    elif not coin.overwintered:
        if tx.version_group_id is not None:
            raise DataError("Version group ID not enabled on this coin.")
        if tx.branch_id is not None:
            raise DataError("Branch ID not enabled on this coin.")

    return tx


def _sanitize_tx_meta(tx: PrevTx, coin: CoinInfo) -> PrevTx:
    if not coin.extra_data and tx.extra_data_len:
        raise DataError("Extra data not enabled on this coin.")

    if coin.decred or coin.overwintered:
        tx.expiry = tx.expiry if tx.expiry is not None else 0
    elif tx.expiry:
        raise DataError("Expiry not enabled on this coin.")

    if coin.timestamp and not tx.timestamp:
        raise DataError("Timestamp must be set.")
    elif not coin.timestamp and tx.timestamp:
        raise DataError("Timestamp not enabled on this coin.")
    elif not coin.overwintered:
        if tx.version_group_id is not None:
            raise DataError("Version group ID not enabled on this coin.")
        if tx.branch_id is not None:
            raise DataError("Branch ID not enabled on this coin.")

    return tx


def _sanitize_tx_input(txi: TxInput, coin: CoinInfo) -> TxInput:
    script_type = txi.script_type  # local_cache_attribute

    if len(txi.prev_hash) != TX_HASH_SIZE:
        raise DataError("Provided prev_hash is invalid.")

    if txi.multisig and script_type not in common.MULTISIG_INPUT_SCRIPT_TYPES:
        raise DataError("Multisig field provided but not expected.")

    if not txi.multisig and script_type == InputScriptType.SPENDMULTISIG:
        raise DataError("Multisig details required.")

    if script_type in common.INTERNAL_INPUT_SCRIPT_TYPES:
        if not txi.address_n:
            raise DataError("Missing address_n field.")

        if txi.script_pubkey:
            raise DataError("Input's script_pubkey provided but not expected.")

        if txi.ownership_proof:
            raise DataError("Ownership proof not expected for internal input.")
    else:
        if txi.address_n:
            raise DataError("Input's address_n provided but not expected.")

        if not txi.script_pubkey:
            raise DataError("Missing script_pubkey field.")

    if not coin.decred and txi.decred_tree is not None:
        raise DataError("Decred details provided but Decred coin not specified.")

    if script_type in common.SEGWIT_INPUT_SCRIPT_TYPES or txi.witness is not None:
        if not coin.segwit:
            raise DataError("Segwit not enabled on this coin.")

    if script_type == InputScriptType.SPENDTAPROOT and not coin.taproot:
        raise DataError("Taproot not enabled on this coin")

    if txi.ownership_proof and (txi.witness or txi.script_sig):
        raise DataError("Ownership proof not expected for presigned input.")

    if txi.commitment_data and not txi.ownership_proof:
        raise DataError("commitment_data field provided but not expected.")

    if txi.orig_hash and txi.orig_index is None:
        raise DataError("Missing orig_index field.")

    return txi


def _sanitize_tx_prev_input(txi: PrevInput, coin: CoinInfo) -> PrevInput:
    if len(txi.prev_hash) != TX_HASH_SIZE:
        raise DataError("Provided prev_hash is invalid.")

    if not coin.decred and txi.decred_tree is not None:
        raise DataError("Decred details provided but Decred coin not specified.")

    return txi


def _sanitize_tx_output(txo: TxOutput, coin: CoinInfo) -> TxOutput:
    script_type = txo.script_type  # local_cache_attribute
    address_n = txo.address_n  # local_cache_attribute

    if txo.multisig and script_type not in common.MULTISIG_OUTPUT_SCRIPT_TYPES:
        raise DataError("Multisig field provided but not expected.")

    if not txo.multisig and script_type == OutputScriptType.PAYTOMULTISIG:
        raise DataError("Multisig details required.")

    if address_n and script_type not in common.CHANGE_OUTPUT_SCRIPT_TYPES:
        raise DataError("Output's address_n provided but not expected.")

    if txo.amount is None:
        raise DataError("Missing amount field.")

    if script_type in common.SEGWIT_OUTPUT_SCRIPT_TYPES:
        if not coin.segwit:
            raise DataError("Segwit not enabled on this coin.")

    if script_type == OutputScriptType.PAYTOTAPROOT and not coin.taproot:
        raise DataError("Taproot not enabled on this coin")

    if script_type == OutputScriptType.PAYTOOPRETURN:
        # op_return output
        if txo.op_return_data is None:
            raise DataError("OP_RETURN output without op_return_data")
        if txo.amount != 0:
            raise DataError("OP_RETURN output with non-zero amount")
        if txo.address or address_n or txo.multisig:
            raise DataError("OP_RETURN output with address or multisig")
    else:
        if txo.op_return_data:
            raise DataError("OP RETURN data provided but not OP RETURN script type.")
        if address_n and txo.address:
            raise DataError("Both address and address_n provided.")
        if not address_n and not txo.address:
            raise DataError("Missing address")

    if txo.orig_hash and txo.orig_index is None:
        raise DataError("Missing orig_index field.")

    return txo
