from trezor.crypto.hashlib import sha256, ripemd160
from trezor.crypto.curve import secp256k1
from trezor.crypto import base58, der
from trezor.utils import ensure

from trezor.messages.CoinType import CoinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TransactionType import TransactionType
from trezor.messages.RequestType import TXINPUT, TXOUTPUT, TXMETA, TXFINISHED
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages import OutputScriptType

from apps.common import address_type
from apps.common import coins
from apps.wallet.sign_tx.segwit_bip143 import *
from apps.wallet.sign_tx.writers import *

# Machine instructions
# ===


class SigningError(ValueError):
    pass


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
    txi.script_type = (
        txi.script_type if txi.script_type is not None else InputScriptType.SPENDADDRESS)
    return txi


def sanitize_tx_output(tx: TransactionType) -> TxOutputType:
    return tx.outputs[0]


def sanitize_tx_binoutput(tx: TransactionType) -> TxOutputBinType:
    return tx.bin_outputs[0]


# Transaction signing
# ===

# Phase 1
# - check inputs, previous transactions, and outputs
# - ask for confirmations
# - check fee
async def check_tx_fee(tx: SignTx, root):

    coin = coins.by_name(tx.coin_name)

    # h_first is used to make sure the inputs and outputs streamed in Phase 1
    # are the same as in Phase 2.  it is thus not required to fully hash the
    # tx, as the SignTx info is streamed only once
    h_first = HashWriter(sha256)  # not a real tx hash
    bip143 = Bip143()

    txo_bin = TxOutputBinType()
    tx_req = TxRequest()
    tx_req.details = TxRequestDetailsType()

    total_in = 0  # sum of input amounts
    total_out = 0  # sum of output amounts
    change_out = 0  # change output amount
    segwit = {}  # dict of booleans stating if input is segwit

    for i in range(tx.inputs_count):
        # STAGE_REQUEST_1_INPUT
        txi = await request_tx_input(tx_req, i)
        write_tx_input_check(h_first, txi)
        if txi.script_type == InputScriptType.SPENDP2SHWITNESS:
            segwit[i] = True
            # Add I to segwit hash_prevouts, hash_sequence
            bip143.add_prevouts(txi)
            bip143.add_sequence(txi)
            total_in += txi.amount
        else:
            segwit[i] = False
            total_in += await get_prevtx_output_value(
                tx_req, txi.prev_hash, txi.prev_index)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_3_OUTPUT
        txo = await request_tx_output(tx_req, o)
        if output_is_change(txo):
            if change_out != 0:
                raise SigningError(FailureType.ProcessError,
                                   'Only one change output is valid')
            change_out = txo.amount
        else:
            if not await confirm_output(txo, coin):
                raise SigningError(FailureType.ActionCancelled,
                                   'Output cancelled')
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, root)
        write_tx_output(h_first, txo_bin)
        bip143.add_output(txo_bin)
        total_out += txo_bin.amount

    fee = total_in - total_out
    if fee < 0:
        raise SigningError(FailureType.NotEnoughFunds,
                           'Not enough funds')

    if fee > coin.maxfee_kb * ((estimate_tx_size(tx.inputs_count, tx.outputs_count) + 999) // 1000):
        if not await confirm_feeoverthreshold(fee, coin):
            raise SigningError(FailureType.ActionCancelled,
                               'Signing cancelled')

    if not await confirm_total(total_out - change_out, fee, coin):
        raise SigningError(FailureType.ActionCancelled,
                           'Total cancelled')

    return h_first, tx_req, txo_bin, bip143, segwit


async def sign_tx(tx: SignTx, root):

    tx = sanitize_sign_tx(tx)

    # Phase 1

    h_first, tx_req, txo_bin, bip143, segwit = await check_tx_fee(tx, root)

    # Phase 2
    # - sign inputs
    # - check that nothing changed

    coin = coins.by_name(tx.coin_name)
    tx_ser = TxRequestSerializedType()

    for i_sign in range(tx.inputs_count):
        # hash of what we are signing with this input
        h_sign = HashWriter(sha256)
        # same as h_first, checked at the end of this iteration
        h_second = HashWriter(sha256)

        txi_sign = None
        key_sign = None
        key_sign_pub = None

        write_uint32(h_sign, tx.version)

        write_varint(h_sign, tx.inputs_count)

        if segwit[i_sign]:
            # STAGE_REQUEST_SEGWIT_INPUT
            txi_sign = await request_tx_input(tx_req, i_sign)
            if txi_sign.script_type == InputScriptType.SPENDP2SHWITNESS:
                key_sign = node_derive(root, txi_sign.address_n)
                key_sign_pub = key_sign.public_key()
                txi_sign.script_sig = input_derive_script(txi_sign, key_sign_pub)
                w_txi = bytearray_with_cap(
                    7 + len(txi_sign.prev_hash) + 4 + len(txi_sign.script_sig) + 4)
                if i_sign == 0:  # serializing first input => prepend meta
                    write_uint32(w_txi, tx.version)
                    write_varint(w_txi, 0x00)  # segwit witness marker
                    write_varint(w_txi, 0x01)  # segwit witness flag
                    write_varint(w_txi, tx.inputs_count)
                write_tx_input(w_txi, txi_sign)
                tx_ser.serialized_tx = w_txi

            tx_req.serialized = tx_ser

        else:
            for i in range(tx.inputs_count):
                # STAGE_REQUEST_4_INPUT
                txi = await request_tx_input(tx_req, i)
                write_tx_input_check(h_second, txi)
                if i == i_sign:
                    txi_sign = txi
                    key_sign = node_derive(root, txi.address_n)
                    key_sign_pub = key_sign.public_key()
                    txi.script_sig = input_derive_script(txi, key_sign_pub)
                else:
                    txi.script_sig = bytes()
                write_tx_input(h_sign, txi)

            write_varint(h_sign, tx.outputs_count)

            for o in range(tx.outputs_count):
                # STAGE_REQUEST_4_OUTPUT
                txo = await request_tx_output(tx_req, o)
                txo_bin.amount = txo.amount
                txo_bin.script_pubkey = output_derive_script(txo, coin, root)
                write_tx_output(h_second, txo_bin)
                write_tx_output(h_sign, txo_bin)

            write_uint32(h_sign, tx.lock_time)

            write_uint32(h_sign, 0x00000001)  # SIGHASH_ALL hash_type

            # check the control digests
            if get_tx_hash(h_first, False) != get_tx_hash(h_second, False):
                raise SigningError(FailureType.ProcessError,
                                   'Transaction has changed during signing')

            # compute the signature from the tx digest
            signature = ecdsa_sign(key_sign, get_tx_hash(h_sign, True))
            tx_ser.signature_index = i_sign
            tx_ser.signature = signature

            # serialize input with correct signature
            txi_sign.script_sig = input_derive_script(
                txi_sign, key_sign_pub, signature)
            w_txi_sign = bytearray_with_cap(
                5 + len(txi_sign.prev_hash) + 4 + len(txi_sign.script_sig) + 4)
            if i_sign == 0:  # serializing first input => prepend tx version and inputs count
                write_uint32(w_txi_sign, tx.version)
                write_varint(w_txi_sign, tx.inputs_count)
            write_tx_input(w_txi_sign, txi_sign)
            tx_ser.serialized_tx = w_txi_sign

            tx_req.serialized = tx_ser

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_5_OUTPUT
        txo = await request_tx_output(tx_req, o)
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, root)

        # serialize output
        w_txo_bin = bytearray_with_cap(
            5 + 8 + 5 + len(txo_bin.script_pubkey) + 4)
        if o == 0:  # serializing first output => prepend outputs count
            write_varint(w_txo_bin, tx.outputs_count)
        write_tx_output(w_txo_bin, txo_bin)

        tx_ser.signature_index = None  # @todo delete?
        tx_ser.signature = None
        tx_ser.serialized_tx = w_txo_bin

        tx_req.serialized = tx_ser

    for i in range(tx.inputs_count):
        if segwit[i]:
            # STAGE_REQUEST_SEGWIT_WITNESS
            txi = await request_tx_input(tx_req, i)
            # todo check amount?
            # if hashType != ANYONE_CAN_PAY ? todo
            # todo: what to do with other types?
            key_sign = node_derive(root, txi.address_n)
            key_sign_pub = key_sign.public_key()
            bip143_hash = bip143.preimage_hash(tx, txi, ecdsa_hash_pubkey(key_sign_pub))

            signature = ecdsa_sign(key_sign, bip143_hash)

            witness = get_p2wpkh_witness(signature, key_sign_pub)

            tx_ser.serialized_tx = witness
            tx_req.serialized = tx_ser
        # else
            # witness is 0x00

    write_uint32(tx_ser.serialized_tx, tx.lock_time)

    await request_tx_finish(tx_req)


async def get_prevtx_output_value(tx_req: TxRequest, prev_hash: bytes, prev_index: int) -> int:
    total_out = 0  # sum of output amounts

    # STAGE_REQUEST_2_PREV_META
    tx = await request_tx_meta(tx_req, prev_hash)

    txh = HashWriter(sha256)

    write_uint32(txh, tx.version)
    write_varint(txh, tx.inputs_cnt)

    for i in range(tx.inputs_cnt):
        # STAGE_REQUEST_2_PREV_INPUT
        txi = await request_tx_input(tx_req, i, prev_hash)
        write_tx_input(txh, txi)

    write_varint(txh, tx.outputs_cnt)

    for o in range(tx.outputs_cnt):
        # STAGE_REQUEST_2_PREV_OUTPUT
        txo_bin = await request_tx_output(tx_req, o, prev_hash)
        write_tx_output(txh, txo_bin)
        if o == prev_index:
            total_out += txo_bin.amount

    write_uint32(txh, tx.lock_time)

    if get_tx_hash(txh, True, True) != prev_hash:
        raise SigningError(FailureType.ProcessError,
                           'Encountered invalid prev_hash')

    return total_out


def estimate_tx_size(inputs, outputs):
    return 10 + inputs * 149 + outputs * 35


# TX Outputs
# ===


def output_derive_script(o: TxOutputType, coin: CoinType, root) -> bytes:
    if o.script_type == OutputScriptType.PAYTOADDRESS:
        ra = output_paytoaddress_extract_raw_address(o, coin, root)
        ra = address_type.strip(coin.address_type, ra)
        return script_paytoaddress_new(ra)

    elif o.script_type == OutputScriptType.PAYTOSCRIPTHASH:
        ra = output_paytoaddress_extract_raw_address(o, coin, root, p2sh=True)
        ra = address_type.strip(coin.address_type_p2sh, ra)
        return script_paytoscripthash_new(ra)

    elif o.script_type == OutputScriptType.PAYTOOPRETURN:
        if o.amount == 0:
            return script_paytoopreturn_new(o.op_return_data)
        else:
            raise SigningError(FailureType.SyntaxError,
                               'OP_RETURN output with non-zero amount')

    else:
        raise SigningError(FailureType.SyntaxError,
                           'Invalid output script type')


def output_paytoaddress_extract_raw_address(
        o: TxOutputType, coin: CoinType, root, p2sh: bool=False) -> bytes:
    # todo if segwit then addr_type = p2sh ?
    addr_type = coin.address_type_p2sh if p2sh else coin.address_type
    # TODO: dont encode/decode more then necessary
    if o.address_n is not None:
        node = node_derive(root, o.address_n)
        address = node.address(addr_type)
        return base58.decode_check(address)
    if o.address:
        raw = base58.decode_check(o.address)
        if not address_type.check(addr_type, raw):
            raise SigningError(FailureType.SyntaxError,
                               'Invalid address type')
        return raw
    raise SigningError(FailureType.SyntaxError,
                       'Missing address')


def output_is_change(o: TxOutputType) -> bool:
    return bool(o.address_n)


# Tx Inputs
# ===


def input_derive_script(i: TxInputType, pubkey: bytes, signature: bytes=None) -> bytes:
    if i.script_type == InputScriptType.SPENDADDRESS:
        if signature is None:
            return script_paytoaddress_new(ecdsa_hash_pubkey(pubkey))
        else:
            return script_spendaddress_new(pubkey, signature)

    if i.script_type == InputScriptType.SPENDP2SHWITNESS:  # p2wpkh using p2sh
        return script_p2wpkh_in_p2sh(ecdsa_hash_pubkey(pubkey))

    else:
        raise SigningError(FailureType.SyntaxError,
                           'Unknown input script type')


def node_derive(root, address_n: list):
    node = root.clone()
    node.derive_path(address_n)
    return node


def ecdsa_hash_pubkey(pubkey: bytes) -> bytes:
    if pubkey[0] == 0x04:
        ensure(len(pubkey) == 65)  # uncompressed format
    elif pubkey[0] == 0x00:
        ensure(len(pubkey) == 1)   # point at infinity
    else:
        ensure(len(pubkey) == 33)  # compresssed format
    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()
    return h


def ecdsa_sign(node, digest: bytes) -> bytes:
    sig = secp256k1.sign(node.private_key(), digest)
    sigder = der.encode_seq((sig[1:33], sig[33:65]))
    return sigder


# TX Scripts
# ===


def script_paytoaddress_new(pubkeyhash: bytes) -> bytearray:
    s = bytearray(25)
    s[0] = 0x76  # OP_DUP
    s[1] = 0xA9  # OP_HASH_160
    s[2] = 0x14  # pushing 20 bytes
    s[3:23] = pubkeyhash
    s[23] = 0x88  # OP_EQUALVERIFY
    s[24] = 0xAC  # OP_CHECKSIG
    return s


def script_paytoscripthash_new(scripthash: bytes) -> bytearray:
    s = bytearray(23)
    s[0] = 0xA9  # OP_HASH_160
    s[1] = 0x14  # pushing 20 bytes
    s[2:22] = scripthash
    s[22] = 0x87  # OP_EQUAL
    return s


# P2WPKH is nested in P2SH to be backwards compatible
# see https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#witness-program
# this pushes 16 00 14 <pubkeyhash>
def script_p2wpkh_in_p2sh(pubkeyhash: bytes) -> bytearray:
    w = bytearray_with_cap(3 + len(pubkeyhash))
    write_op_push(w, len(pubkeyhash) + 2)  # 0x16 - length of the redeemScript
    w.append(0x00)  # witness version byte
    w.append(0x14)  # P2WPKH witness program (pub key hash length + pub key hash)
    write_bytes(w, pubkeyhash)
    return w


def script_paytoopreturn_new(data: bytes) -> bytearray:
    w = bytearray_with_cap(1 + 5 + len(data))
    w.append(0x6A)  # OP_RETURN
    write_op_push(w, len(data))
    w.extend(data)
    return w


def script_spendaddress_new(pubkey: bytes, signature: bytes) -> bytearray:
    w = bytearray_with_cap(5 + len(signature) + 1 + 5 + len(pubkey))
    append_signature_and_pubkey(w, pubkey, signature)
    return w


def get_p2wpkh_witness(signature: bytes, pubkey: bytes):
    w = bytearray_with_cap(1 + 5 + len(signature) + 1 + 5 + len(pubkey))
    write_varint(w, 0x02)  # num of segwit items, in P2WPKH it's always 2
    append_signature_and_pubkey(w, pubkey, signature)
    return w


def append_signature_and_pubkey(w: bytearray, pubkey: bytes, signature: bytes) -> bytearray:
    write_op_push(w, len(signature) + 1)
    write_bytes(w, signature)
    w.append(0x01)  # SIGHASH_ALL
    write_op_push(w, len(pubkey))
    write_bytes(w, pubkey)
    return w
