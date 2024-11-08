from typing import TYPE_CHECKING

from trezor import utils
from trezor.enums import RequestType
from trezor.wire import DataError

from .. import common
from ..writers import TX_HASH_SIZE
from . import layout

if TYPE_CHECKING:
    from typing import Any, Awaitable

    from trezor.enums import AmountUnit
    from trezor.messages import (
        PrevInput,
        PrevOutput,
        PrevTx,
        SignTx,
        TxAckPaymentRequest,
        TxInput,
        TxOutput,
        TxRequest,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.paths import Bip32Path

# Machine instructions
# ===


class UiConfirm:
    def confirm_dialog(self) -> Awaitable[Any]:
        raise NotImplementedError

    __eq__ = utils.obj_eq


class UiConfirmOutput(UiConfirm):
    def __init__(
        self,
        output: TxOutput,
        coin: CoinInfo,
        amount_unit: AmountUnit,
        output_index: int,
        chunkify: bool,
        address_n: Bip32Path | None,
    ) -> None:
        self.output = output
        self.coin = coin
        self.amount_unit = amount_unit
        self.output_index = output_index
        self.chunkify = chunkify
        self.address_n = address_n

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_output(
            self.output,
            self.coin,
            self.amount_unit,
            self.output_index,
            self.chunkify,
            self.address_n,
        )


class UiConfirmDecredSSTXSubmission(UiConfirm):
    def __init__(
        self, output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit
    ) -> None:
        self.output = output
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_decred_sstx_submission(
            self.output, self.coin, self.amount_unit
        )


class UiConfirmPaymentRequest(UiConfirm):
    def __init__(
        self,
        payment_req: TxAckPaymentRequest,
        coin: CoinInfo,
        amount_unit: AmountUnit,
    ) -> None:
        self.payment_req = payment_req
        self.amount_unit = amount_unit
        self.coin = coin

    def confirm_dialog(self) -> Awaitable[bool]:
        return layout.should_show_payment_request_details(
            self.payment_req, self.coin, self.amount_unit
        )

    __eq__ = utils.obj_eq


class UiConfirmReplacement(UiConfirm):
    def __init__(self, title: str, txid: bytes) -> None:
        self.title = title
        self.txid = txid

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_replacement(self.title, self.txid)


class UiConfirmModifyOutput(UiConfirm):
    def __init__(
        self,
        txo: TxOutput,
        orig_txo: TxOutput,
        coin: CoinInfo,
        amount_unit: AmountUnit,
    ) -> None:
        self.txo = txo
        self.orig_txo = orig_txo
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_modify_output(
            self.txo, self.orig_txo, self.coin, self.amount_unit
        )


class UiConfirmModifyFee(UiConfirm):
    def __init__(
        self,
        title: str,
        user_fee_change: int,
        total_fee_new: int,
        fee_rate: float,
        coin: CoinInfo,
        amount_unit: AmountUnit,
    ) -> None:
        self.title = title
        self.user_fee_change = user_fee_change
        self.total_fee_new = total_fee_new
        self.fee_rate = fee_rate
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_modify_fee(
            self.title,
            self.user_fee_change,
            self.total_fee_new,
            self.fee_rate,
            self.coin,
            self.amount_unit,
        )


class UiConfirmTotal(UiConfirm):
    def __init__(
        self,
        spending: int,
        fee: int,
        fee_rate: float,
        coin: CoinInfo,
        amount_unit: AmountUnit,
        address_n: Bip32Path | None,
    ) -> None:
        self.spending = spending
        self.fee = fee
        self.fee_rate = fee_rate
        self.coin = coin
        self.amount_unit = amount_unit
        self.address_n = address_n

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_total(
            self.spending,
            self.fee,
            self.fee_rate,
            self.coin,
            self.amount_unit,
            self.address_n,
        )


class UiConfirmJointTotal(UiConfirm):
    def __init__(
        self, spending: int, total: int, coin: CoinInfo, amount_unit: AmountUnit
    ) -> None:
        self.spending = spending
        self.total = total
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_joint_total(
            self.spending, self.total, self.coin, self.amount_unit
        )


class UiConfirmFeeOverThreshold(UiConfirm):
    def __init__(self, fee: int, coin: CoinInfo, amount_unit: AmountUnit) -> None:
        self.fee = fee
        self.coin = coin
        self.amount_unit = amount_unit

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_feeoverthreshold(self.fee, self.coin, self.amount_unit)


class UiConfirmChangeCountOverThreshold(UiConfirm):
    def __init__(self, change_count: int) -> None:
        self.change_count = change_count

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_change_count_over_threshold(self.change_count)


class UiConfirmUnverifiedExternalInput(UiConfirm):
    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_unverified_external_input()


class UiConfirmForeignAddress(UiConfirm):
    def __init__(self, address_n: list) -> None:
        self.address_n = address_n

    def confirm_dialog(self) -> Awaitable[Any]:
        from apps.common import paths

        return paths.show_path_warning(self.address_n)


class UiConfirmNonDefaultLocktime(UiConfirm):
    def __init__(self, lock_time: int, lock_time_disabled: bool) -> None:
        self.lock_time = lock_time
        self.lock_time_disabled = lock_time_disabled

    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_nondefault_locktime(
            self.lock_time, self.lock_time_disabled
        )


class UiConfirmMultipleAccounts(UiConfirm):
    def confirm_dialog(self) -> Awaitable[Any]:
        return layout.confirm_multiple_accounts()


def confirm_output(output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit, output_index: int, chunkify: bool, address_n: Bip32Path | None) -> Awaitable[None]:  # type: ignore [awaitable-return-type]
    return (
        yield UiConfirmOutput(  # type: ignore [awaitable-return-type]
            output, coin, amount_unit, output_index, chunkify, address_n
        )
    )


def confirm_decred_sstx_submission(output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[None]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmDecredSSTXSubmission(output, coin, amount_unit))  # type: ignore [awaitable-return-type]


def should_show_payment_request_details(payment_req: TxAckPaymentRequest, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[bool]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmPaymentRequest(payment_req, coin, amount_unit))  # type: ignore [awaitable-return-type]


def confirm_replacement(description: str, txid: bytes) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmReplacement(description, txid))  # type: ignore [awaitable-return-type]


def confirm_modify_output(txo: TxOutput, orig_txo: TxOutput, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmModifyOutput(txo, orig_txo, coin, amount_unit))  # type: ignore [awaitable-return-type]


def confirm_modify_fee(title: str, user_fee_change: int, total_fee_new: int, fee_rate: float, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (
        yield UiConfirmModifyFee(  # type: ignore [awaitable-return-type]
            title, user_fee_change, total_fee_new, fee_rate, coin, amount_unit
        )
    )


def confirm_total(spending: int, fee: int, fee_rate: float, coin: CoinInfo, amount_unit: AmountUnit, address_n: Bip32Path | None) -> Awaitable[None]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmTotal(spending, fee, fee_rate, coin, amount_unit, address_n))  # type: ignore [awaitable-return-type]


def confirm_joint_total(spending: int, total: int, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmJointTotal(spending, total, coin, amount_unit))  # type: ignore [awaitable-return-type]


def confirm_feeoverthreshold(fee: int, coin: CoinInfo, amount_unit: AmountUnit) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmFeeOverThreshold(fee, coin, amount_unit))  # type: ignore [awaitable-return-type]


def confirm_change_count_over_threshold(change_count: int) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmChangeCountOverThreshold(change_count))  # type: ignore [awaitable-return-type]


def confirm_unverified_external_input() -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmUnverifiedExternalInput())  # type: ignore [awaitable-return-type]


def confirm_foreign_address(address_n: list) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmForeignAddress(address_n))  # type: ignore [awaitable-return-type]


def confirm_nondefault_locktime(lock_time: int, lock_time_disabled: bool) -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmNonDefaultLocktime(lock_time, lock_time_disabled))  # type: ignore [awaitable-return-type]


def confirm_multiple_accounts() -> Awaitable[Any]:  # type: ignore [awaitable-return-type]
    return (yield UiConfirmMultipleAccounts())  # type: ignore [awaitable-return-type]


def request_tx_meta(tx_req: TxRequest, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[PrevTx]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckPrevMeta

    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXMETA
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevMeta, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    return _sanitize_tx_meta(ack.tx, coin)


def request_tx_extra_data(
    tx_req: TxRequest, offset: int, size: int, tx_hash: bytes | None = None
) -> Awaitable[bytearray]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckPrevExtraData

    details = tx_req.details  # local_cache_attribute

    assert details is not None
    tx_req.request_type = RequestType.TXEXTRADATA
    details.extra_data_offset = offset
    details.extra_data_len = size
    details.tx_hash = tx_hash
    ack = yield TxAckPrevExtraData, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    return ack.tx.extra_data_chunk


def request_tx_input(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[TxInput]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckInput

    assert tx_req.details is not None
    if tx_hash:
        tx_req.request_type = RequestType.TXORIGINPUT
        tx_req.details.tx_hash = tx_hash
    else:
        tx_req.request_type = RequestType.TXINPUT
    tx_req.details.request_index = i
    ack = yield TxAckInput, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    return _sanitize_tx_input(ack.tx.input, coin)


def request_tx_prev_input(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[PrevInput]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckPrevInput

    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevInput, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    return _sanitize_tx_prev_input(ack.tx.input, coin)


def request_tx_output(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[TxOutput]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckOutput

    assert tx_req.details is not None
    if tx_hash:
        tx_req.request_type = RequestType.TXORIGOUTPUT
        tx_req.details.tx_hash = tx_hash
    else:
        tx_req.request_type = RequestType.TXOUTPUT
    tx_req.details.request_index = i
    ack = yield TxAckOutput, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    return _sanitize_tx_output(ack.tx.output, coin)


def request_tx_prev_output(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes | None = None) -> Awaitable[PrevOutput]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckPrevOutput

    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield TxAckPrevOutput, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    # return sanitize_tx_prev_output(ack.tx, coin)  # no sanitize is required
    return ack.tx.output


def request_payment_req(tx_req: TxRequest, i: int) -> Awaitable[TxAckPaymentRequest]:  # type: ignore [awaitable-return-type]
    from trezor.messages import TxAckPaymentRequest

    assert tx_req.details is not None
    tx_req.request_type = RequestType.TXPAYMENTREQ
    tx_req.details.request_index = i
    ack = yield TxAckPaymentRequest, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)
    return _sanitize_payment_req(ack)


def request_tx_finish(tx_req: TxRequest) -> Awaitable[None]:  # type: ignore [awaitable-return-type]
    tx_req.request_type = RequestType.TXFINISHED
    yield None, tx_req  # type: ignore [awaitable-return-type]
    _clear_tx_request(tx_req)


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
    from trezor.enums import InputScriptType
    from trezor.wire import DataError  # local_cache_global

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
    from trezor.enums import OutputScriptType
    from trezor.wire import DataError  # local_cache_global

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


def _sanitize_payment_req(payment_req: TxAckPaymentRequest) -> TxAckPaymentRequest:
    for memo in payment_req.memos:
        if (memo.text_memo, memo.refund_memo, memo.coin_purchase_memo).count(None) != 2:
            raise DataError(
                "Exactly one memo type must be specified in each PaymentRequestMemo."
            )

    return payment_req
