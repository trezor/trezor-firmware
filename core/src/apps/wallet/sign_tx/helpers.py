import gc

from trezor import utils
from trezor.messages import FailureType, InputScriptType, OutputScriptType
from trezor.messages.RequestType import (
    TXEXTRADATA,
    TXFINISHED,
    TXINPUT,
    TXMETA,
    TXOUTPUT,
)
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequest import TxRequest

from .signing import SigningError
from .writers import TX_HASH_SIZE

from apps.common.coininfo import CoinInfo

if False:
    from typing import Any, Awaitable, Union

MULTISIG_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDMULTISIG,
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
)
MULTISIG_OUTPUT_SCRIPT_TYPES = (
    OutputScriptType.PAYTOMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS,
)

CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES = {
    OutputScriptType.PAYTOADDRESS: InputScriptType.SPENDADDRESS,
    OutputScriptType.PAYTOMULTISIG: InputScriptType.SPENDMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS: InputScriptType.SPENDP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS: InputScriptType.SPENDWITNESS,
}
INTERNAL_INPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.values())
CHANGE_OUTPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.keys())

SEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
)

NONSEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDADDRESS,
    InputScriptType.SPENDMULTISIG,
)

# Machine instructions
# ===


class UiConfirmOutput:
    def __init__(self, output: TxOutputType, coin: CoinInfo):
        self.output = output
        self.coin = coin

    __eq__ = utils.obj_eq


class UiConfirmTotal:
    def __init__(self, spending: int, fee: int, coin: CoinInfo):
        self.spending = spending
        self.fee = fee
        self.coin = coin

    __eq__ = utils.obj_eq


class UiConfirmFeeOverThreshold:
    def __init__(self, fee: int, coin: CoinInfo):
        self.fee = fee
        self.coin = coin

    __eq__ = utils.obj_eq


class UiConfirmForeignAddress:
    def __init__(self, address_n: list):
        self.address_n = address_n

    __eq__ = utils.obj_eq


class UiConfirmNonDefaultLocktime:
    def __init__(self, lock_time: int):
        self.lock_time = lock_time

    __eq__ = utils.obj_eq


def confirm_output(output: TxOutputType, coin: CoinInfo) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmOutput(output, coin))


def confirm_total(spending: int, fee: int, coin: CoinInfo) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmTotal(spending, fee, coin))


def confirm_feeoverthreshold(fee: int, coin: CoinInfo) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmFeeOverThreshold(fee, coin))


def confirm_foreign_address(address_n: list) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmForeignAddress(address_n))


def confirm_nondefault_locktime(lock_time: int) -> Awaitable[Any]:  # type: ignore
    return (yield UiConfirmNonDefaultLocktime(lock_time))


def request_tx_meta(tx_req: TxRequest, coin: CoinInfo, tx_hash: bytes = None) -> Awaitable[Any]:  # type: ignore
    tx_req.request_type = TXMETA
    tx_req.details.tx_hash = tx_hash
    tx_req.details.request_index = None
    ack = yield tx_req
    tx_req.serialized.signature = None
    tx_req.serialized.signature_index = None
    tx_req.serialized.serialized_tx[:] = bytes()
    gc.collect()
    return sanitize_tx_meta(ack.tx, coin)


def request_tx_extra_data(  # type: ignore
    tx_req: TxRequest, offset: int, size: int, tx_hash: bytes = None
) -> Awaitable[Any]:
    tx_req.request_type = TXEXTRADATA
    tx_req.details.extra_data_offset = offset
    tx_req.details.extra_data_len = size
    tx_req.details.tx_hash = tx_hash
    tx_req.details.request_index = None
    ack = yield tx_req
    tx_req.serialized.signature = None
    tx_req.serialized.signature_index = None
    tx_req.serialized.serialized_tx[:] = bytes()
    tx_req.details.extra_data_offset = None
    tx_req.details.extra_data_len = None
    gc.collect()
    return ack.tx.extra_data


def request_tx_input(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes = None) -> Awaitable[Any]:  # type: ignore
    tx_req.request_type = TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized.signature = None
    tx_req.serialized.signature_index = None
    tx_req.serialized.serialized_tx[:] = bytes()
    gc.collect()
    return sanitize_tx_input(ack.tx, coin)


def request_tx_output(tx_req: TxRequest, i: int, coin: CoinInfo, tx_hash: bytes = None) -> Awaitable[Any]:  # type: ignore
    tx_req.request_type = TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized.signature = None
    tx_req.serialized.signature_index = None
    tx_req.serialized.serialized_tx[:] = bytes()
    gc.collect()
    if tx_hash is None:
        return sanitize_tx_output(ack.tx, coin)
    else:
        return sanitize_tx_binoutput(ack.tx, coin)


def request_tx_finish(tx_req: TxRequest) -> Awaitable[Any]:  # type: ignore
    tx_req.request_type = TXFINISHED
    tx_req.details = None
    yield tx_req
    tx_req.serialized.signature = None
    tx_req.serialized.signature_index = None
    tx_req.serialized.serialized_tx[:] = bytes()
    gc.collect()


# Data sanitizers
# ===


def sanitize_sign_tx(tx: SignTx, coin: CoinInfo) -> SignTx:
    tx.version = tx.version if tx.version is not None else 1
    tx.lock_time = tx.lock_time if tx.lock_time is not None else 0
    tx.inputs_count = tx.inputs_count if tx.inputs_count is not None else 0
    tx.outputs_count = tx.outputs_count if tx.outputs_count is not None else 0
    tx.coin_name = tx.coin_name if tx.coin_name is not None else "Bitcoin"
    if coin.decred or coin.overwintered:
        tx.expiry = tx.expiry if tx.expiry is not None else 0
    elif tx.expiry:
        raise SigningError(FailureType.DataError, "Expiry not enabled on this coin.")
    if coin.timestamp and not tx.timestamp:
        raise SigningError(FailureType.DataError, "Timestamp must be set.")
    elif not coin.timestamp and tx.timestamp:
        raise SigningError(FailureType.DataError, "Timestamp not enabled on this coin.")
    return tx


def sanitize_tx_meta(tx: TransactionType, coin: CoinInfo) -> TransactionType:
    tx.version = tx.version if tx.version is not None else 1
    tx.lock_time = tx.lock_time if tx.lock_time is not None else 0
    tx.inputs_cnt = tx.inputs_cnt if tx.inputs_cnt is not None else 0
    tx.outputs_cnt = tx.outputs_cnt if tx.outputs_cnt is not None else 0
    if coin.extra_data:
        tx.extra_data_len = tx.extra_data_len if tx.extra_data_len is not None else 0
    elif tx.extra_data_len:
        raise SigningError(
            FailureType.DataError, "Extra data not enabled on this coin."
        )
    if coin.decred or coin.overwintered:
        tx.expiry = tx.expiry if tx.expiry is not None else 0
    elif tx.expiry:
        raise SigningError(FailureType.DataError, "Expiry not enabled on this coin.")
    if coin.timestamp and not tx.timestamp:
        raise SigningError(FailureType.DataError, "Timestamp must be set.")
    elif not coin.timestamp and tx.timestamp:
        raise SigningError(FailureType.DataError, "Timestamp not enabled on this coin.")
    return tx


def sanitize_tx_input(tx: TransactionType, coin: CoinInfo) -> TxInputType:
    txi = tx.inputs[0]
    if txi.script_type is None:
        txi.script_type = InputScriptType.SPENDADDRESS
    if txi.sequence is None:
        txi.sequence = 0xFFFFFFFF
    if txi.prev_hash is None or len(txi.prev_hash) != TX_HASH_SIZE:
        raise SigningError(FailureType.DataError, "Provided prev_hash is invalid.")
    if txi.multisig and txi.script_type not in MULTISIG_INPUT_SCRIPT_TYPES:
        raise SigningError(
            FailureType.DataError, "Multisig field provided but not expected.",
        )
    if txi.address_n and txi.script_type not in INTERNAL_INPUT_SCRIPT_TYPES:
        raise SigningError(
            FailureType.DataError, "Input's address_n provided but not expected.",
        )
    if not coin.decred and txi.decred_tree is not None:
        raise SigningError(
            FailureType.DataError,
            "Decred details provided but Decred coin not specified.",
        )
    if txi.script_type in SEGWIT_INPUT_SCRIPT_TYPES:
        if not coin.segwit:
            raise SigningError(
                FailureType.DataError, "Segwit not enabled on this coin",
            )
        if txi.amount is None:
            raise SigningError(
                FailureType.DataError, "Segwit input without amount",
            )

    _sanitize_decred(txi, coin)
    return txi


def sanitize_tx_output(tx: TransactionType, coin: CoinInfo) -> TxOutputType:
    txo = tx.outputs[0]
    if txo.multisig and txo.script_type not in MULTISIG_OUTPUT_SCRIPT_TYPES:
        raise SigningError(
            FailureType.DataError, "Multisig field provided but not expected.",
        )
    if txo.address_n and txo.script_type not in CHANGE_OUTPUT_SCRIPT_TYPES:
        raise SigningError(
            FailureType.DataError, "Output's address_n provided but not expected.",
        )
    if txo.script_type == OutputScriptType.PAYTOOPRETURN:
        # op_return output
        if txo.amount != 0:
            raise SigningError(
                FailureType.DataError, "OP_RETURN output with non-zero amount"
            )
        if txo.address or txo.address_n or txo.multisig:
            raise SigningError(
                FailureType.DataError, "OP_RETURN output with address or multisig"
            )
    else:
        if txo.op_return_data:
            raise SigningError(
                FailureType.DataError,
                "OP RETURN data provided but not OP RETURN script type.",
            )
        if txo.address_n and txo.address:
            raise SigningError(
                FailureType.DataError, "Both address and address_n provided."
            )
        if not txo.address_n and not txo.address:
            raise SigningError(FailureType.DataError, "Missing address")

    _sanitize_decred(txo, coin)

    return txo


def sanitize_tx_binoutput(tx: TransactionType, coin: CoinInfo) -> TxOutputBinType:
    txo_bin = tx.bin_outputs[0]
    _sanitize_decred(txo_bin, coin)
    return txo_bin


def _sanitize_decred(
    tx: Union[TxInputType, TxOutputType, TxOutputBinType], coin: CoinInfo
) -> None:
    if not coin.decred and tx.decred_script_version is not None:
        raise SigningError(
            FailureType.DataError,
            "Decred details provided but Decred coin not specified.",
        )
