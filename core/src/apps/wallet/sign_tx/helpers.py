import gc

from trezor.messages import InputScriptType
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
from trezor.utils import obj_eq

from apps.common.coininfo import CoinInfo

# Machine instructions
# ===


class UiConfirmOutput:
    def __init__(self, output: TxOutputType, coin: CoinInfo):
        self.output = output
        self.coin = coin

    __eq__ = obj_eq


class UiConfirmTotal:
    def __init__(self, spending: int, fee: int, coin: CoinInfo):
        self.spending = spending
        self.fee = fee
        self.coin = coin

    __eq__ = obj_eq


class UiConfirmFeeOverThreshold:
    def __init__(self, fee: int, coin: CoinInfo):
        self.fee = fee
        self.coin = coin

    __eq__ = obj_eq


class UiConfirmForeignAddress:
    def __init__(self, address_n: list):
        self.address_n = address_n

    __eq__ = obj_eq


class UiConfirmNonDefaultLocktime:
    def __init__(self, lock_time: int):
        self.lock_time = lock_time

    __eq__ = obj_eq


def confirm_output(output: TxOutputType, coin: CoinInfo):
    return (yield UiConfirmOutput(output, coin))


def confirm_total(spending: int, fee: int, coin: CoinInfo):
    return (yield UiConfirmTotal(spending, fee, coin))


def confirm_feeoverthreshold(fee: int, coin: CoinInfo):
    return (yield UiConfirmFeeOverThreshold(fee, coin))


def confirm_foreign_address(address_n: list):
    return (yield UiConfirmForeignAddress(address_n))


def confirm_nondefault_locktime(lock_time: int):
    return (yield UiConfirmNonDefaultLocktime(lock_time))


def request_tx_meta(tx_req: TxRequest, tx_hash: bytes = None):
    tx_req.request_type = TXMETA
    tx_req.details.tx_hash = tx_hash
    tx_req.details.request_index = None
    ack = yield tx_req
    tx_req.serialized = None
    gc.collect()
    return sanitize_tx_meta(ack.tx)


def request_tx_extra_data(
    tx_req: TxRequest, offset: int, size: int, tx_hash: bytes = None
):
    tx_req.request_type = TXEXTRADATA
    tx_req.details.extra_data_offset = offset
    tx_req.details.extra_data_len = size
    tx_req.details.tx_hash = tx_hash
    tx_req.details.request_index = None
    ack = yield tx_req
    tx_req.serialized = None
    tx_req.details.extra_data_offset = None
    tx_req.details.extra_data_len = None
    gc.collect()
    return ack.tx.extra_data


def request_tx_input(tx_req: TxRequest, i: int, tx_hash: bytes = None):
    tx_req.request_type = TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized = None
    gc.collect()
    return sanitize_tx_input(ack.tx)


def request_tx_output(tx_req: TxRequest, i: int, tx_hash: bytes = None):
    tx_req.request_type = TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized = None
    gc.collect()
    if tx_hash is None:
        return sanitize_tx_output(ack.tx)
    else:
        return sanitize_tx_binoutput(ack.tx)


def request_tx_finish(tx_req: TxRequest):
    tx_req.request_type = TXFINISHED
    tx_req.details = None
    yield tx_req
    tx_req.serialized = None
    gc.collect()


# Data sanitizers
# ===


def sanitize_sign_tx(tx: SignTx) -> SignTx:
    tx.version = tx.version if tx.version is not None else 1
    tx.lock_time = tx.lock_time if tx.lock_time is not None else 0
    tx.inputs_count = tx.inputs_count if tx.inputs_count is not None else 0
    tx.outputs_count = tx.outputs_count if tx.outputs_count is not None else 0
    tx.coin_name = tx.coin_name if tx.coin_name is not None else "Bitcoin"
    tx.expiry = tx.expiry if tx.expiry is not None else 0
    tx.overwintered = tx.overwintered if tx.overwintered is not None else False
    tx.timestamp = tx.timestamp if tx.timestamp is not None else 0
    return tx


def sanitize_tx_meta(tx: TransactionType) -> TransactionType:
    tx.version = tx.version if tx.version is not None else 1
    tx.lock_time = tx.lock_time if tx.lock_time is not None else 0
    tx.inputs_cnt = tx.inputs_cnt if tx.inputs_cnt is not None else 0
    tx.outputs_cnt = tx.outputs_cnt if tx.outputs_cnt is not None else 0
    tx.extra_data_len = tx.extra_data_len if tx.extra_data_len is not None else 0
    tx.expiry = tx.expiry if tx.expiry is not None else 0
    tx.overwintered = tx.overwintered if tx.overwintered is not None else False
    tx.timestamp = tx.timestamp if tx.timestamp is not None else 0
    return tx


def sanitize_tx_input(tx: TransactionType) -> TxInputType:
    txi = tx.inputs[0]
    if txi.script_type is None:
        txi.script_type = InputScriptType.SPENDADDRESS
    if txi.sequence is None:
        txi.sequence = 0xFFFFFFFF
    return txi


def sanitize_tx_output(tx: TransactionType) -> TxOutputType:
    return tx.outputs[0]


def sanitize_tx_binoutput(tx: TransactionType) -> TxOutputBinType:
    return tx.bin_outputs[0]
