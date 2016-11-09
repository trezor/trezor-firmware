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
from trezor.messages import OutputScriptType, InputScriptType


# Machine instructions
# ===


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
                raise ValueError('Only one change output is valid')
            change_out = txo.amount
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, root)
        write_tx_output(h_first, txo_bin)
        total_out += txo_bin.amount
        # TODO: display output
        # TODO: confirm output

    # TODO: check funds and tx fee
    # TODO: ask for confirmation

    # Phase 2
    # - sign inputs
    # - check that nothing changed

    tx_ser = TxRequestSerializedType()

    for i_sign in range(tx_inputs_count):
        # hash of what we are signing with this input
        h_sign = HashWriter(sha256)
        # h_sign = BufferWriter()
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
                txi.script_sig = input_derive_script_pre_sign(
                    txi, key_sign_pub)
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

        write_uint32(h_sign, 0x0000001) # hash_type

        # check the control digests
        if tx_hash_digest(h_first, False) != tx_hash_digest(h_second, False):
            raise ValueError('Transaction has changed during signing')

        # compute the signature from the tx digest
        signature = ecdsa_sign(key_sign, tx_hash_digest(h_sign, True))
        tx_ser.signature_index = i_sign
        tx_ser.signature = signature

        # serialize input with correct signature
        txi_sign.script_sig = input_derive_script_post_sign(
            txi_sign, key_sign_pub, signature)
        w_txi_sign = BufferWriter()
        if i_sign == 0: # serializing first input => prepend tx version and inputs count
            write_uint32(w_txi_sign, tx_version)
            write_varint(w_txi_sign, tx_inputs_count)
        write_tx_input(w_txi_sign, txi_sign)
        tx_ser.serialized_tx = w_txi_sign.getvalue()

        tx_req.serialized = tx_ser

    for o in range(tx_outputs_count):
        # STAGE_REQUEST_5_OUTPUT
        txo = await request_tx_output(tx_req, o)
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, root)

        # serialize output
        w_txo_bin = BufferWriter()
        if o == 0: # serializing first output => prepend outputs count
            write_varint(w_txo_bin, tx_outputs_count)
        write_tx_output(w_txo_bin, txo_bin)
        if o == tx_outputs_count - 1: # serializing last output => append tx lock_time
            write_uint32(w_txo_bin, tx_lock_time)
        tx_ser.signature_index = None
        tx_ser.signature = None
        tx_ser.serialized_tx = w_txo_bin.getvalue()

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

    prev_hash_rev = bytes(reversed(prev_hash))  # TODO: improve performance
    if tx_hash_digest(txh, True) != prev_hash_rev:
        raise ValueError('Encountered invalid prev_hash')

    return total_out


def tx_hash_digest(w, double: bool) -> bytes:
    d = w.getvalue()
    if double:
        d = sha256(d).digest()
    return d


# TX Outputs
# ===


def output_derive_script(o: TxOutputType, coin: CoinType, root) -> bytes:
    if o.script_type == OutputScriptType.PAYTOADDRESS:
        ra = output_paytoaddress_extract_raw_address(o, coin, root)
        return script_paytoaddress_new(ra[1:])
    else:
        raise ValueError('Invalid output script type')
    return


def output_paytoaddress_extract_raw_address(o: TxOutputType, coin: CoinType, root) -> bytes:
    o_address_n = getattr(o, 'address_n', None)
    o_address = getattr(o, 'address', None)
    # TODO: dont encode/decode more then necessary
    # TODO: detect correct address type
    if o_address_n is not None:
        n = node_derive(root, o_address_n)
        raw_address = base58.decode_check(n.address())
    elif o_address:
        raw_address = base58.decode_check(o_address)
    else:
        raise ValueError('Missing address')
    if raw_address[0] != coin['address_type']:
        raise ValueError('Invalid address type')
    return raw_address


def output_is_change(output: TxOutputType):
    address_n = getattr(output, 'address_n', None)
    return bool(address_n)


# Tx Inputs
# ===


def input_derive_script_pre_sign(i: TxInputType, pubkey: bytes) -> bytes:
    i_script_type = getattr(i, 'script_type', InputScriptType.SPENDADDRESS)
    if i_script_type == InputScriptType.SPENDADDRESS:
        return script_paytoaddress_new(ecdsa_hash_pubkey(pubkey))
    else:
        raise ValueError('Unknown input script type')


def input_derive_script_post_sign(i: TxInputType, pubkey: bytes, signature: bytes) -> bytes:
    i_script_type = getattr(i, 'script_type', InputScriptType.SPENDADDRESS)
    if i_script_type == InputScriptType.SPENDADDRESS:
        return script_spendaddress_new(pubkey, signature)
    else:
        raise ValueError('Unknown input script type')


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


def script_spendaddress_new(pubkey: bytes, signature: bytes) -> bytearray:
    w = BufferWriter()
    write_op_push(w, len(signature) + 1)
    write_bytes(w, signature)
    w.writebyte(0x01)
    write_op_push(w, len(pubkey))
    write_bytes(w, pubkey)
    return w.getvalue()


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
    wb = w.writebyte
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
    wb = w.writebyte
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
    wb = w.writebyte
    wb(n & 0xFF)
    wb((n >> 8) & 0xFF)
    wb((n >> 16) & 0xFF)
    wb((n >> 24) & 0xFF)


def write_uint64(w, n: int):
    wb = w.writebyte
    wb(n & 0xFF)
    wb((n >> 8) & 0xFF)
    wb((n >> 16) & 0xFF)
    wb((n >> 24) & 0xFF)
    wb((n >> 32) & 0xFF)
    wb((n >> 40) & 0xFF)
    wb((n >> 48) & 0xFF)
    wb((n >> 56) & 0xFF)


def write_bytes(w, buf: bytearray):
    w.write(buf)


def write_bytes_rev(w, buf: bytearray):
    w.write(bytearray(reversed(buf)))


class BufferWriter:

    def __init__(self, buf: bytearray=None):
        if buf is None:
            buf = bytearray()
        self.buf = buf

    def write(self, buf: bytearray):
        self.buf.extend(buf)

    def writebyte(self, b: int):
        self.buf.append(b)

    def getvalue(self) -> bytearray:
        return self.buf


class HashWriter:

    def __init__(self, hashfunc):
        self.ctx = hashfunc()
        self.buf = bytearray(1)  # used in writebyte()

    def write(self, buf: bytearray):
        self.ctx.update(buf)

    def writebyte(self, b: int):
        self.buf[0] = b
        self.ctx.update(self.buf)

    def getvalue(self) -> bytes:
        return self.ctx.digest()
