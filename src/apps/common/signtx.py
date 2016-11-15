from trezor.crypto.hashlib import sha256, ripemd160
from trezor.crypto.curve import secp256k1
from trezor.crypto import base58, der

from . import coins

from trezor.messages.CoinType import CoinType
from trezor.messages.SignTx import SignTx
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.RequestType import TXINPUT, TXOUTPUT, TXMETA, TXFINISHED
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages import OutputScriptType, InputScriptType, FailureType


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


def confirm_output(output: TxOutputType, coin: CoinType):
    return (yield UiConfirmOutput(output, coin))


def confirm_total(spending: int, fee: int, coin: CoinType):
    return (yield UiConfirmTotal(spending, fee, coin))


def request_tx_meta(tx_req: TxRequest, tx_hash: bytes=None):
    tx_req.request_type = TXMETA
    tx_req.details.tx_hash = tx_hash
    tx_req.details.request_index = None
    ack = yield tx_req
    tx_req.serialized = None
    return ack.tx


def request_tx_input(tx_req: TxRequest, i: int, tx_hash: bytes=None):
    tx_req.request_type = TXINPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized = None
    return ack.tx.inputs[0]


def request_tx_output(tx_req: TxRequest, i: int, tx_hash: bytes=None):
    tx_req.request_type = TXOUTPUT
    tx_req.details.request_index = i
    tx_req.details.tx_hash = tx_hash
    ack = yield tx_req
    tx_req.serialized = None
    if tx_hash is None:
        return ack.tx.outputs[0]
    else:
        return ack.tx.bin_outputs[0]


def request_tx_finish(tx_req: TxRequest):
    tx_req.request_type = TXFINISHED
    tx_req.details = None
    yield tx_req
    tx_req.serialized = None


# Transaction signing
# ===


async def sign_tx(tx: SignTx, root):
    tx_version = getattr(tx, 'version', 1)
    tx_lock_time = getattr(tx, 'lock_time', 0)
    tx_inputs_count = getattr(tx, 'inputs_count', 0)
    tx_outputs_count = getattr(tx, 'outputs_count', 0)
    coin_name = getattr(tx, 'coin_name', 'Bitcoin')

    coin = coins.by_name(coin_name)

    # Phase 1
    # - check inputs, previous transactions, and outputs
    # - ask for confirmations
    # - check fee

    total_in = 0  # sum of input amounts
    total_out = 0  # sum of output amounts
    change_out = 0  # change output amount

    # h_first is used to make sure the inputs and outputs streamed in Phase 1
    # are the same as in Phase 2.  it is thus not required to fully hash the
    # tx, as the SignTx info is streamed only once
    h_first = HashWriter(sha256)  # not a real tx hash

    txo_bin = TxOutputBinType()
    tx_req = TxRequest()
    tx_req.details = TxRequestDetailsType()

    for i in range(tx_inputs_count):
        # STAGE_REQUEST_1_INPUT
        txi = await request_tx_input(tx_req, i)
        write_tx_input_check(h_first, txi)
        total_in += await get_prevtx_output_value(
            tx_req, txi.prev_hash, txi.prev_index)

    for o in range(tx_outputs_count):
        # STAGE_REQUEST_3_OUTPUT
        txo = await request_tx_output(tx_req, o)
        if output_is_change(txo):
            if change_out != 0:
                raise SigningError(FailureType.Other,
                                   'Only one change output is valid')
            change_out = txo.amount
        else:
            if not await confirm_output(txo, coin):
                raise SigningError(FailureType.ActionCancelled,
                                   'Output cancelled')
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, root)
        write_tx_output(h_first, txo_bin)
        total_out += txo_bin.amount

    fee = total_in - total_out

    if fee < 0:
        raise SigningError(FailureType.NotEnoughFunds,
                           'Not enough funds')

    if not await confirm_total(total_out - change_out, fee, coin):
        raise SigningError(FailureType.ActionCancelled,
                           'Total cancelled')

    # Phase 2
    # - sign inputs
    # - check that nothing changed

    tx_ser = TxRequestSerializedType()

    for i_sign in range(tx_inputs_count):
        # hash of what we are signing with this input
        h_sign = HashWriter(sha256)
        # same as h_first, checked at the end of this iteration
        h_second = HashWriter(sha256)

        txi_sign = None
        key_sign = None
        key_sign_pub = None

        write_uint32(h_sign, tx_version)

        write_varint(h_sign, tx_inputs_count)

        for i in range(tx_inputs_count):
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

        write_varint(h_sign, tx_outputs_count)

        for o in range(tx_outputs_count):
            # STAGE_REQUEST_4_OUTPUT
            txo = await request_tx_output(tx_req, o)
            txo_bin.amount = txo.amount
            txo_bin.script_pubkey = output_derive_script(txo, coin, root)
            write_tx_output(h_second, txo_bin)
            write_tx_output(h_sign, txo_bin)

        write_uint32(h_sign, tx_lock_time)

        write_uint32(h_sign, 0x00000001)  # SIGHASH_ALL hash_type

        # check the control digests
        if get_tx_hash(h_first, False) != get_tx_hash(h_second, False):
            raise SigningError(FailureType.Other,
                               'Transaction has changed during signing')

        # compute the signature from the tx digest
        signature = ecdsa_sign(key_sign, get_tx_hash(h_sign, True))
        tx_ser.signature_index = i_sign
        tx_ser.signature = signature

        # serialize input with correct signature
        txi_sign.script_sig = input_derive_script(
            txi_sign, key_sign_pub, signature)
        w_txi_sign = bytearray()
        if i_sign == 0:  # serializing first input => prepend tx version and inputs count
            write_uint32(w_txi_sign, tx_version)
            write_varint(w_txi_sign, tx_inputs_count)
        write_tx_input(w_txi_sign, txi_sign)
        tx_ser.serialized_tx = w_txi_sign

        tx_req.serialized = tx_ser

    for o in range(tx_outputs_count):
        # STAGE_REQUEST_5_OUTPUT
        txo = await request_tx_output(tx_req, o)
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, root)

        # serialize output
        w_txo_bin = bytearray()
        if o == 0:  # serializing first output => prepend outputs count
            write_varint(w_txo_bin, tx_outputs_count)
        write_tx_output(w_txo_bin, txo_bin)
        if o == tx_outputs_count - 1:  # serializing last output => append tx lock_time
            write_uint32(w_txo_bin, tx_lock_time)
        tx_ser.signature_index = None
        tx_ser.signature = None
        tx_ser.serialized_tx = w_txo_bin

        tx_req.serialized = tx_ser

    await request_tx_finish(tx_req)


async def get_prevtx_output_value(tx_req: TxRequest, prev_hash: bytes, prev_index: int) -> int:
    total_out = 0  # sum of output amounts

    # STAGE_REQUEST_2_PREV_META
    tx = await request_tx_meta(tx_req, prev_hash)

    tx_version = getattr(tx, 'version', 0)
    tx_lock_time = getattr(tx, 'lock_time', 1)
    tx_inputs_count = getattr(tx, 'inputs_cnt', 0)
    tx_outputs_count = getattr(tx, 'outputs_cnt', 0)

    txh = HashWriter(sha256)

    write_uint32(txh, tx_version)

    write_varint(txh, tx_inputs_count)

    for i in range(tx_inputs_count):
        # STAGE_REQUEST_2_PREV_INPUT
        txi = await request_tx_input(tx_req, i, prev_hash)
        write_tx_input(txh, txi)

    write_varint(txh, tx_outputs_count)

    for o in range(tx_outputs_count):
        # STAGE_REQUEST_2_PREV_OUTPUT
        txo_bin = await request_tx_output(tx_req, o, prev_hash)
        write_tx_output(txh, txo_bin)
        if o == prev_index:
            total_out += txo_bin.amount

    write_uint32(txh, tx_lock_time)

    if get_tx_hash(txh, True, True) != prev_hash:
        raise SigningError(FailureType.Other,
                           'Encountered invalid prev_hash')

    return total_out


def get_tx_hash(w, double: bool, reverse: bool=False) -> bytes:
    d = w.getvalue()
    if double:
        d = sha256(d).digest()
    if reverse:
        d = bytes(reversed(d))
    return d


# TX Outputs
# ===


def output_derive_script(o: TxOutputType, coin: CoinType, root) -> bytes:
    if o.script_type == OutputScriptType.PAYTOADDRESS:
        ra = output_paytoaddress_extract_raw_address(o, coin, root)
        return script_paytoaddress_new(ra[1:])
    elif o.script_type == OutputScriptType.PAYTOSCRIPTHASH:
        ra = output_paytoaddress_extract_raw_address(o, coin, root, p2sh=True)
        return script_paytoscripthash_new(ra[1:])
    else:
        raise SigningError(FailureType.SyntaxError,
                           'Invalid output script type')
    return


def check_address_type(address_type, raw_address):
    if address_type <= 0xFF:
        return address_type == raw_address[0]
    if address_type <= 0xFFFF:
        return address_type == (raw_address[0] << 8) | raw_address[1]
    if address_type <= 0xFFFFFF:
        return address_type == (raw_address[0] << 16) | (raw_address[1] << 8) | raw_address[2]
    # else
    return address_type == (raw_address[0] << 24) | (raw_address[1] << 16) | (raw_address[2] << 8) | raw_address[3]

def output_paytoaddress_extract_raw_address(o: TxOutputType, coin: CoinType, root, p2sh=False) -> bytes:
    address_type = coin.address_type_p2sh if p2sh else coin.address_type
    # TODO: dont encode/decode more then necessary
    address_n = getattr(o, 'address_n', None)
    if address_n is not None:
        node = node_derive(root, address_n)
        address = node.address(address_type)
        return base58.decode_check(address)
    address = getattr(o, 'address', None)
    if address:
        raw = base58.decode_check(address)
        if not check_address_type(address_type, raw):
            raise SigningError(FailureType.SyntaxError,
                               'Invalid address type')
        return raw
    raise SigningError(FailureType.SyntaxError,
                       'Missing address')


def output_is_change(o: TxOutputType):
    address_n = getattr(o, 'address_n', None)
    return bool(address_n)


# Tx Inputs
# ===


def input_derive_script(i: TxInputType, pubkey: bytes, signature: bytes = None) -> bytes:
    i_script_type = getattr(i, 'script_type', InputScriptType.SPENDADDRESS)
    if i_script_type == InputScriptType.SPENDADDRESS:
        if signature is None:
            return script_paytoaddress_new(ecdsa_hash_pubkey(pubkey))
        else:
            return script_spendaddress_new(pubkey, signature)
    else:
        raise SigningError(FailureType.SyntaxError,
                           'Unknown input script type')


def node_derive(root, address_n: list):
    node = root.clone()
    node.derive_path(address_n)
    return node


def ecdsa_hash_pubkey(pubkey: bytes) -> bytes:
    if pubkey[0] == 0x04:
        assert len(pubkey) == 65  # uncompressed format
    elif pubkey[0] == 0x00:
        assert len(pubkey) == 1   # point at infinity
    else:
        assert len(pubkey) == 33  # compresssed format
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

def script_spendaddress_new(pubkey: bytes, signature: bytes) -> bytearray:
    w = bytearray()
    write_op_push(w, len(signature) + 1)
    write_bytes(w, signature)
    w.append(0x01)
    write_op_push(w, len(pubkey))
    write_bytes(w, pubkey)
    return w


# TX Serialization
# ===

def write_tx_input(w, i: TxInputType):
    i_sequence = getattr(i, 'sequence', 4294967295)
    write_bytes_rev(w, i.prev_hash)
    write_uint32(w, i.prev_index)
    write_varint(w, len(i.script_sig))
    write_bytes(w, i.script_sig)
    write_uint32(w, i_sequence)


def write_tx_input_check(w, i: TxInputType):
    i_sequence = getattr(i, 'sequence', 4294967295)
    write_bytes(w, i.prev_hash)
    write_uint32(w, i.prev_index)
    write_uint32(w, len(i.address_n))
    for n in i.address_n:
        write_uint32(w, n)
    write_uint32(w, i_sequence)


def write_tx_output(w, o: TxOutputBinType):
    write_uint64(w, o.amount)
    write_varint(w, len(o.script_pubkey))
    write_bytes(w, o.script_pubkey)


def write_op_push(w, n: int):
    wb = w.append
    if n < 0x4C:
        wb(n & 0xFF)
    elif n < 0xFF:
        wb(0x4C)
        wb(n & 0xFF)
    elif n < 0xFFFF:
        wb(0x4D)
        wb(n & 0xFF)
        wb((n >> 8) & 0xFF)
    else:
        wb(0x4E)
        wb(n & 0xFF)
        wb((n >> 8) & 0xFF)
        wb((n >> 16) & 0xFF)
        wb((n >> 24) & 0xFF)


# Buffer IO & Serialization
# ===


def write_varint(w, n: int):
    wb = w.append
    if n < 253:
        wb(n & 0xFF)
    elif n < 65536:
        wb(253)
        wb(n & 0xFF)
        wb((n >> 8) & 0xFF)
    else:
        wb(254)
        wb(n & 0xFF)
        wb((n >> 8) & 0xFF)
        wb((n >> 16) & 0xFF)
        wb((n >> 24) & 0xFF)


def write_uint32(w, n: int):
    wb = w.append
    wb(n & 0xFF)
    wb((n >> 8) & 0xFF)
    wb((n >> 16) & 0xFF)
    wb((n >> 24) & 0xFF)


def write_uint64(w, n: int):
    wb = w.append
    wb(n & 0xFF)
    wb((n >> 8) & 0xFF)
    wb((n >> 16) & 0xFF)
    wb((n >> 24) & 0xFF)
    wb((n >> 32) & 0xFF)
    wb((n >> 40) & 0xFF)
    wb((n >> 48) & 0xFF)
    wb((n >> 56) & 0xFF)


def write_bytes(w, buf: bytearray):
    w.extend(buf)


def write_bytes_rev(w, buf: bytearray):
    w.extend(bytearray(reversed(buf)))


class HashWriter:

    def __init__(self, hashfunc):
        self.ctx = hashfunc()
        self.buf = bytearray(1)  # used in append()

    def extend(self, buf: bytearray):
        self.ctx.update(buf)

    def append(self, b: int):
        self.buf[0] = b
        self.ctx.update(self.buf)

    def getvalue(self) -> bytes:
        return self.ctx.digest()
