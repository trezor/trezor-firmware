
from trezor.messages.CoinType import CoinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.SignTx import SignTx
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TransactionType import TransactionType
from trezor.messages.RequestType import TXINPUT, TXOUTPUT, TXMETA, TXFINISHED
from trezor.messages import InputScriptType

# Machine instructions
# ===


class UiConfirmOutput:

    def __init__(self, output: TxOutputType, coin: CoinType):
        self.output = output
        self.coin = coin


class UiConfirmTotal:

    def __init__(self, spending: int, fee: int, coin: CoinType):
        self.spending = spending
        self.fee = fee
        self.coin = coin


class UiConfirmFeeOverThreshold:

    def __init__(self, fee: int, coin: CoinType):
        self.fee = fee
        self.coin = coin


def confirm_output(output: TxOutputType, coin: CoinType):
    return (yield UiConfirmOutput(output, coin))


def confirm_total(spending: int, fee: int, coin: CoinType):
    return (yield UiConfirmTotal(spending, fee, coin))


def confirm_feeoverthreshold(fee: int, coin: CoinType):
    return (yield UiConfirmFeeOverThreshold(fee, coin))


def request_tx_meta(tx_req: TxRequest, tx_hash: bytes=None):
    tx_req.request_type = TXMETA
    tx_req.details.tx_hash = tx_hash
    tx_req.details.request_index = None
    ack = yield tx_req
    tx_req.serialized = None
    return sanitize_tx_meta(ack.tx)


def request_tx_input(tx_req: TxRequest, i: int, tx_hash: bytes=None):
    tx_req.request_type = TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized = None
    return sanitize_tx_input(ack.tx)


def request_tx_output(tx_req: TxRequest, i: int, tx_hash: bytes=None):
    tx_req.request_type = TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized = None
    if tx_hash is None:
        return sanitize_tx_output(ack.tx)
    else:
        return sanitize_tx_binoutput(ack.tx)


def request_tx_finish(tx_req: TxRequest):
    tx_req.request_type = TXFINISHED
    tx_req.details = None
    yield tx_req
    tx_req.serialized = None


# Data sanitizers
# ===


def sanitize_sign_tx(tx: SignTx) -> SignTx:
    tx.version = tx.version if tx.version is not None else 1
    tx.lock_time = tx.lock_time if tx.lock_time is not None else 0
    tx.inputs_count = tx.inputs_count if tx.inputs_count is not None else 0
    tx.outputs_count = tx.outputs_count if tx.outputs_count is not None else 0
    tx.coin_name = tx.coin_name if tx.coin_name is not None else 'Bitcoin'
    return tx


def sanitize_tx_meta(tx: TransactionType) -> TransactionType:
    tx.version = tx.version if tx.version is not None else 1
    tx.lock_time = tx.lock_time if tx.lock_time is not None else 0
    tx.inputs_cnt = tx.inputs_cnt if tx.inputs_cnt is not None else 0
    tx.outputs_cnt = tx.outputs_cnt if tx.outputs_cnt is not None else 0
    return tx


def sanitize_tx_input(tx: TransactionType) -> TxInputType:
    txi = tx.inputs[0]
    if txi.script_type is None:
        txi.script_type = InputScriptType.SPENDADDRESS
    if txi.sequence is None:
        txi.sequence = 4294967295
    return txi


def sanitize_tx_output(tx: TransactionType) -> TxOutputType:
    return tx.outputs[0]


def sanitize_tx_binoutput(tx: TransactionType) -> TxOutputBinType:
    return tx.bin_outputs[0]

