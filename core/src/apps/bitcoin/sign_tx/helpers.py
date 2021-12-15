from trezor import utils, wire
from trezor.enums import InputScriptType, OutputScriptType, RequestType
from trezor.messages import (
    PrevInput,
    PrevOutput,
    PrevTx,
    SignTx,
    TxAckInput,
    TxAckOutput,
    TxAckPrevExtraData,
    TxAckPrevInput,
    TxAckPrevMeta,
    TxAckPrevOutput,
    TxInput,
    TxOutput,
    TxRequest,
)

from apps.common import paths
from apps.common.coininfo import CoinInfo

from .. import common
from ..writers import TX_HASH_SIZE
from . import layout

if False:
    from typing import Any, Awaitable
    from trezor.enums import AmountUnit


# Machine instructions
# ===


class UiConfirm:
    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        raise NotImplementedError


class UiConfirmOutput(UiConfirm):
    def __init__(self, output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit):
        self.output = output
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_output(ctx, self.output, self.coin, self.amount_unit)

    __eq__ = utils.obj_eq


class UiConfirmDecredSSTXSubmission(UiConfirm):
    def __init__(self, output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit):
        self.output = output
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_decred_sstx_submission(
            ctx, self.output, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmReplacement(UiConfirm):
    def __init__(self, description: str, txid: bytes):
        self.description = description
        self.txid = txid

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_replacement(ctx, self.description, self.txid)

    __eq__ = utils.obj_eq


class UiConfirmModifyOutput(UiConfirm):
    def __init__(
        self,
        txo: TxOutput,
        orig_txo: TxOutput,
        coin: CoinInfo,
        amount_unit: AmountUnit,
    ):
        self.txo = txo
        self.orig_txo = orig_txo
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_modify_output(
            ctx, self.txo, self.orig_txo, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmModifyFee(UiConfirm):
    def __init__(
        self,
        user_fee_change: int,
        total_fee_new: int,
        coin: CoinInfo,
        amount_unit: AmountUnit,
    ):
        self.user_fee_change = user_fee_change
        self.total_fee_new = total_fee_new
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_modify_fee(
            ctx, self.user_fee_change, self.total_fee_new, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmTotal(UiConfirm):
    def __init__(
        self, spending: int, fee: int, coin: CoinInfo, amount_unit: AmountUnit
    ):
        self.spending = spending
        self.fee = fee
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_total(
            ctx, self.spending, self.fee, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmJointTotal(UiConfirm):
    def __init__(
        self, spending: int, total: int, coin: CoinInfo, amount_unit: AmountUnit
    ):
        self.spending = spending
        self.total = total
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_joint_total(
            ctx, self.spending, self.total, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmFeeOverThreshold(UiConfirm):
    def __init__(self, fee: int, coin: CoinInfo, amount_unit: AmountUnit):
        self.fee = fee
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_feeoverthreshold(
            ctx, self.fee, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmChangeCountOverThreshold(UiConfirm):
    def __init__(self, change_count: int):
        self.change_count = change_count

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_change_count_over_threshold(ctx, self.change_count)

    __eq__ = utils.obj_eq


class UiConfirmForeignAddress(UiConfirm):
    def __init__(self, address_n: list):
        self.address_n = address_n

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return paths.show_path_warning(ctx, self.address_n)

    __eq__ = utils.obj_eq


class UiConfirmNonDefaultLocktime(UiConfirm):
    def __init__(self, lock_time: int, lock_time_disabled: bool):
        self.lock_time = lock_time
        self.lock_time_disabled = lock_time_disabled

    def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
        return layout.confirm_nondefault_locktime(
            ctx, self.lock_time, self.lock_time_disabled
        )

    __eq__ = utils.obj_eq


def confirm_output(output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[None]:  # type: ignore
    return (yield UiConfirmOutput(output, coin, amount_unit))


def confirm_decred_sstx_submission(output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[None]:  # type: ignore
    return (yield UiConfirmDecredSSTXSubmission(output, coin, amount_unit))


def confirm_replacement(description: str, txid: bytes) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmReplacement(description, txid))


def confirm_modify_output(txo: TxOutput, orig_txo: TxOutput, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmModifyOutput(txo, orig_txo, coin, amount_unit))


def confirm_modify_fee(user_fee_change: int, total_fee_new: int, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmModifyFee(user_fee_change, total_fee_new, coin, amount_unit))


def confirm_total(spending: int, fee: int, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[None]:  # type: ignore
    return (yield UiConfirmTotal(spending, fee, coin, amount_unit))


def confirm_joint_total(spending: int, total: int, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmJointTotal(spending, total, coin, amount_unit))


def confirm_feeoverthreshold(fee: int, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmFeeOverThreshold(fee, coin, amount_unit))


def confirm_change_count_over_threshold(change_count: int) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmChangeCountOverThreshold(change_count))


def confirm_foreign_address(address_n: list) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmForeignAddress(address_n))


def confirm_nondefault_locktime(lock_time: int, lock_time_disabled: bool) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmNonDefaultLocktime(lock_time, lock_time_disabled))


def request_tx_meta(tx_req: TxRequest, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[PrevTx]:  # type: ignore
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXMETA
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevMeta, tx_req
    _clear_tx_request(tx_req)
    return sanitize_tx_meta(ack.tx, coin)


def request_tx_extra_data(  # type: ignore
    tx_req: TxRequest, offset: int, size: int, tx_hash: bytes | None = None
) -> Awaitable[bytearray]:
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXEXTRADATA
    tx_req.details.extra_data_offset = offset
    tx_req.details.extra_data_len = size
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevExtraData, tx_req
    _clear_tx_request(tx_req)
    return ack.tx.extra_data_chunk


def request_tx_input(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[TxInput]:  # type: ignore
    assert tx_req.details is not None
    if tx_hash:
        tx_req.request_type = RequestType.TXORIGINPUT
        tx_req.details.tx_hash = tx_hash
    else:
        tx_req.request_type = RequestType.TXINPUT
    tx_req.details.request_index = i
    ack = yield TxAckInput, tx_req
    _clear_tx_request(tx_req)
    return sanitize_tx_input(ack.tx.input, coin)


def request_tx_prev_input(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[PrevInput]:  # type: ignore
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevInput, tx_req
    _clear_tx_request(tx_req)
    return sanitize_tx_prev_input(ack.tx.input, coin)


def request_tx_output(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[TxOutput]:  # type: ignore
    assert tx_req.details is not None
    if tx_hash:
        tx_req.request_type = RequestType.TXORIGOUTPUT
        tx_req.details.tx_hash = tx_hash
    else:
        tx_req.request_type = RequestType.TXOUTPUT
    tx_req.details.request_index = i
    ack = yield TxAckOutput, tx_req
    _clear_tx_request(tx_req)
    return sanitize_tx_output(ack.tx.output, coin)


def request_tx_prev_output(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[PrevOutput]:  # type: ignore
    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevOutput, tx_req
    _clear_tx_request(tx_req)
    # return sanitize_tx_prev_output(ack.tx, coin)  # no sanitize is required
    return ack.tx.output


def request_tx_finish(tx_req: TxRequest) -> Awaitable[None]:  # type: ignore
    tx_req.request_type = RequestType.TXFINISHED
    yield None, tx_req
    _clear_tx_request(tx_req)


def _clear_tx_request(tx_req: TxRequest) -> None:
    assert tx_req.details is not None
    assert tx_req.serialized is not None
    assert tx_req.serialized.serialized_tx is not None
    tx_req.request_type = None
    tx_req.details.request_index = None
    tx_req.details.tx_hash = None
    tx_req.details.extra_data_len = None
    tx_req.details.extra_data_offset = None
    tx_req.serialized.signature = None
    tx_req.serialized.signature_index = None
    # mypy thinks serialized_tx is `bytes`, which doesn't support indexed assignment
    tx_req.serialized.serialized_tx[:] = bytes()  # type: ignore


# Data sanitizers
# ===


def sanitize_sign_tx(tx: SignTx, coin: CoinInfo) -> SignTx:
    if coin.decred or coin.overwintered:
        tx.expiry = tx.expiry if tx.expiry is not None else 0
    elif tx.expiry:
        raise wire.DataError("Expiry not enabled on this coin.")

    if coin.timestamp and not tx.timestamp:
        raise wire.DataError("Timestamp must be set.")
    elif not coin.timestamp and tx.timestamp:
        raise wire.DataError("Timestamp not enabled on this coin.")

    if coin.overwintered:
        if tx.version_group_id is None:
            raise wire.DataError("Version group ID must be set.")
        if tx.branch_id is None:
            raise wire.DataError("Branch ID must be set.")
    elif not coin.overwintered:
        if tx.version_group_id is not None:
            raise wire.DataError("Version group ID not enabled on this coin.")
        if tx.branch_id is not None:
            raise wire.DataError("Branch ID not enabled on this coin.")

    return tx


def sanitize_tx_meta(tx: PrevTx, coin: CoinInfo) -> PrevTx:
    if not coin.extra_data and tx.extra_data_len:
        raise wire.DataError("Extra data not enabled on this coin.")

    if coin.decred or coin.overwintered:
        tx.expiry = tx.expiry if tx.expiry is not None else 0
    elif tx.expiry:
        raise wire.DataError("Expiry not enabled on this coin.")

    if coin.timestamp and not tx.timestamp:
        raise wire.DataError("Timestamp must be set.")
    elif not coin.timestamp and tx.timestamp:
        raise wire.DataError("Timestamp not enabled on this coin.")
    elif not coin.overwintered:
        if tx.version_group_id is not None:
            raise wire.DataError("Version group ID not enabled on this coin.")
        if tx.branch_id is not None:
            raise wire.DataError("Branch ID not enabled on this coin.")

    return tx


def sanitize_tx_input(txi: TxInput, coin: CoinInfo) -> TxInput:
    if len(txi.prev_hash) != TX_HASH_SIZE:
        raise wire.DataError("Provided prev_hash is invalid.")

    if txi.multisig and txi.script_type not in common.MULTISIG_INPUT_SCRIPT_TYPES:
        raise wire.DataError("Multisig field provided but not expected.")

    if not txi.multisig and txi.script_type == InputScriptType.SPENDMULTISIG:
        raise wire.DataError("Multisig details required.")

    if txi.script_type in common.INTERNAL_INPUT_SCRIPT_TYPES:
        if not txi.address_n:
            raise wire.DataError("Missing address_n field.")

        if txi.script_pubkey:
            raise wire.DataError("Input's script_pubkey provided but not expected.")
    else:
        if txi.address_n:
            raise wire.DataError("Input's address_n provided but not expected.")

        if not txi.script_pubkey:
            raise wire.DataError("Missing script_pubkey field.")

    if not coin.decred and txi.decred_tree is not None:
        raise wire.DataError("Decred details provided but Decred coin not specified.")

    if txi.script_type in common.SEGWIT_INPUT_SCRIPT_TYPES or txi.witness is not None:
        if not coin.segwit:
            raise wire.DataError("Segwit not enabled on this coin.")

    if txi.script_type == InputScriptType.SPENDTAPROOT and not coin.taproot:
        raise wire.DataError("Taproot not enabled on this coin")

    if txi.commitment_data and not txi.ownership_proof:
        raise wire.DataError("commitment_data field provided but not expected.")

    if txi.orig_hash and txi.orig_index is None:
        raise wire.DataError("Missing orig_index field.")

    return txi


def sanitize_tx_prev_input(txi: PrevInput, coin: CoinInfo) -> PrevInput:
    if len(txi.prev_hash) != TX_HASH_SIZE:
        raise wire.DataError("Provided prev_hash is invalid.")

    if not coin.decred and txi.decred_tree is not None:
        raise wire.DataError("Decred details provided but Decred coin not specified.")

    return txi


def sanitize_tx_output(txo: TxOutput, coin: CoinInfo) -> TxOutput:
    if txo.multisig and txo.script_type not in common.MULTISIG_OUTPUT_SCRIPT_TYPES:
        raise wire.DataError("Multisig field provided but not expected.")

    if not txo.multisig and txo.script_type == OutputScriptType.PAYTOMULTISIG:
        raise wire.DataError("Multisig details required.")

    if txo.address_n and txo.script_type not in common.CHANGE_OUTPUT_SCRIPT_TYPES:
        raise wire.DataError("Output's address_n provided but not expected.")

    if txo.amount is None:
        raise wire.DataError("Missing amount field.")

    if txo.script_type in common.SEGWIT_OUTPUT_SCRIPT_TYPES:
        if not coin.segwit:
            raise wire.DataError("Segwit not enabled on this coin.")

    if txo.script_type == OutputScriptType.PAYTOTAPROOT and not coin.taproot:
        raise wire.DataError("Taproot not enabled on this coin")

    if txo.script_type == OutputScriptType.PAYTOOPRETURN:
        # op_return output
        if txo.op_return_data is None:
            raise wire.DataError("OP_RETURN output without op_return_data")
        if txo.amount != 0:
            raise wire.DataError("OP_RETURN output with non-zero amount")
        if txo.address or txo.address_n or txo.multisig:
            raise wire.DataError("OP_RETURN output with address or multisig")
    else:
        if txo.op_return_data:
            raise wire.DataError(
                "OP RETURN data provided but not OP RETURN script type."
            )
        if txo.address_n and txo.address:
            raise wire.DataError("Both address and address_n provided.")
        if not txo.address_n and not txo.address:
            raise wire.DataError("Missing address")

    if txo.orig_hash and txo.orig_index is None:
        raise wire.DataError("Missing orig_index field.")

    return txo
