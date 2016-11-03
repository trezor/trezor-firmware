from trezor.crypto.hashlib import sha256, ripemd160
from trezor.crypto.curve import secp256k1
from trezor.crypto import HDNode, base58

from . import coins

from trezor.messages.CoinType import CoinType
from trezor.messages.SignTx import SignTx
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.RequestType import TXINPUT, TXOUTPUT, TXMETA, TXFINISHED
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.messages import OutputScriptType, InputScriptType

# pylint: disable=W0622


# Machine instructions
# ===

# TODO: we might want to define these in terms of data instead
# - like TxRequest, but also for deriving keys for example
# - sign_tx would turn to more or less pure code
# - PROBLEM: async defs in python cannot yield. we could ignore that,
# or use wrappers anyway, or just make it an ordinary old-style coroutine
# and use yield / yield from everywhere


def request_tx_meta(prev_hash: bytes=None):
    ack = yield TxRequest(type=TXMETA, prev_hash=prev_hash)
    return ack.tx


def request_tx_input(index: int, prev_hash: bytes=None):
    ack = yield TxRequest(type=TXINPUT, prev_hash=prev_hash, index=index)
    return ack.tx.inputs[0]


def request_tx_output(index: int, prev_hash: bytes=None):
    ack = yield TxRequest(type=TXOUTPUT, prev_hash=prev_hash, index=index)
    if prev_hash is not None:
        return ack.bin_outputs[0]
    else:
        return ack.outputs[0]


def request_tx_finish():
    yield TxRequest(type=TXFINISHED)


def send_serialized_tx(serialized: TxRequestSerializedType):
    yield serialized


# Transaction signing
# ===


async def sign_tx(tx: SignTx, root: HDNode):
    coin = coins.by_name(tx.coin_name)

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
    h_first = tx_hash_init()  # not a real tx hash

    for i in range(tx.inputs_count):
        # STAGE_REQUEST_1_INPUT
        input = await request_tx_input(i)
        tx_write_input(h_first, input)
        total_in += await get_prevtx_output_value(input.prev_hash, input.prev_index)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_3_OUTPUT
        output = await request_tx_output(o)
        if output_is_change(output):
            if change_out != 0:
                raise ValueError('Only one change output allowed')
            change_out = output.amount
        outputbin = output_compile(output, coin, root)
        tx_write_output(h_first, outputbin)
        total_out += outputbin.amount
        # TODO: display output
        # TODO: confirm output

    h_first_dig = tx_hash_digest(h_first)

    # TODO: check funds and tx fee
    # TODO: ask for confirmation

    # Phase 2
    # - sign inputs
    # - check that nothing changed

    for i_sign in range(tx.inputs_count):
        h_sign = tx_hash_init()  # hash of what we are signing with this input
        h_second = tx_hash_init()  # should be the same as h_first

        input_sign = None
        key_sign = None
        key_sign_pub = None

        for i in range(tx.inputs_count):
            # STAGE_REQUEST_4_INPUT
            input = await request_tx_input(i)
            tx_write_input(h_second, input)
            if i == i_sign:
                key_sign = node_derive(root, input.address_n)
                key_sign_pub = key_sign.public_key()
                script_sig = input_derive_script_pre_sign(input, key_sign_pub)
                input_sign = input
            else:
                script_sig = bytes()
            input.script_sig = script_sig
            tx_write_input(h_sign, input)

        for o in range(tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT
            output = await request_tx_output(o)
            outputbin = output_compile(output, coin, root)
            tx_write_output(h_second, outputbin)
            tx_write_output(h_sign, outputbin)

        if h_first_dig != tx_hash_digest(h_second):
            raise ValueError('Transaction has changed during signing')

        signature = ecdsa_sign(key_sign, tx_hash_digest(h_sign))
        script_sig = input_derive_script_post_sign(
            input, key_sign_pub, signature)
        input_sign.script_sig = script_sig

        # TODO: serialize the whole input at once, including the script_sig
        input_sign_w = BufferWriter(bytearray(), 0)
        tx_write_input(input_sign_w, input_sign)
        input_sign_b = input_sign_w.getvalue()

        serialized = TxRequestSerializedType(
            signature_index=i_sign, signature=signature, serialized_tx=input_sign_b)
        await send_serialized_tx(serialized)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_5_OUTPUT
        output = await request_tx_output(o)
        outputbin = output_compile(output, coin, root)

        outputbin_w = BufferWriter(bytearray(), 0)
        tx_write_input(outputbin_w, outputbin)
        outputbin_b = outputbin_w.getvalue()

        serialized = TxRequestSerializedType(serialized_tx=outputbin_b)
        await send_serialized_tx(serialized)

    await request_tx_finish()


async def get_prevtx_output_value(prev_hash: bytes, prev_index: int) -> int:

    total_in = 0

    # STAGE_REQUEST_2_PREV_META
    tx = await request_tx_meta(prev_hash)

    h = tx_hash_init()
    tx_write_header(h, tx.version, tx.inputs_count)

    for i in range(tx.inputs_count):
        # STAGE_REQUEST_2_PREV_INPUT
        input = await request_tx_input(i, prev_hash)
        tx_write_input(h, input)

    tx_write_middle(h, tx.outputs_count)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_2_PREV_OUTPUT
        outputbin = await request_tx_output(o, prev_hash)
        tx_write_output(h, outputbin)
        if o == prev_index:
            total_in += outputbin.value

    tx_write_footer(h, tx.locktime, False)

    if tx_hash_digest(h) != prev_hash:
        raise ValueError('PrevTx mismatch')

    return total_in


# TX Hashing
# ===


def tx_hash_init():
    return HashWriter(sha256)


def tx_hash_digest(w):
    return sha256(w.getvalue()).digest()


# TX Outputs
# ===


def output_compile(output: TxOutputType, coin: CoinType, root: HDNode) -> TxOutputBinType:
    bin = TxOutputBinType()
    bin.amount = output.amount
    bin.script_pubkey = output_derive_script(output, coin, root)
    return bin


def output_derive_script(output: TxOutputType, coin: CoinType, root: HDNode) -> bytes:
    if output.script_type == OutputScriptType.PAYTOADDRESS:
        raw_address = output_paytoaddress_extract_raw_address(output, root)
        if raw_address[0] != coin.address_type:  # TODO: do this properly
            raise ValueError('Invalid address type')
        return script_paytoaddress_new(raw_address)
    else:
        # TODO: other output script types
        raise ValueError('Unknown output script type')
    return


def output_paytoaddress_extract_raw_address(o: TxOutputType, root: HDNode) -> bytes:
    o_address_n = getattr(o, 'address_n', None)
    o_address = getattr(o, 'address', None)
    if o_address_n:
        node = node_derive(root, o_address_n)
        # TODO: dont encode and decode again
        raw_address = base58.decode_check(node.address())
    elif o_address:
        raw_address = base58.decode_check(o_address)
    else:
        raise ValueError('Missing address')
    return raw_address


def script_paytoaddress_new(raw_address: bytes) -> bytearray:
    s = bytearray(25)
    s[0] = 0x76  # OP_DUP
    s[1] = 0xA9  # OP_HASH_160
    s[2] = 0x14  # pushing 20 bytes
    s[3:23] = raw_address[1:]  # TODO: do this properly
    s[23] = 0x88  # OP_EQUALVERIFY
    s[24] = 0xAC  # OP_CHECKSIG
    return s


def output_is_change(output: TxOutputType):
    address_n = getattr(output, 'address_n', None)
    return bool(address_n)


# Tx Inputs
# ===


def input_derive_script_pre_sign(input: TxInputType, pubkey: bytes) -> bytes:
    if input.script_type == InputScriptType.SPENDADDRESS:
        return script_paytoaddress_new(ecdsa_get_pubkeyhash(pubkey))
    else:
        # TODO: other input script types
        raise ValueError('Unknown input script type')


def input_derive_script_post_sign(input: TxInputType, pubkey: bytes, signature: bytes) -> bytes:
    if input.script_type == InputScriptType.SPENDADDRESS:
        return script_spendaddress_new(pubkey, signature)
    else:
        # TODO: other input script types
        raise ValueError('Unknown input script type')


def script_spendaddress_new(pubkey: bytes, signature: bytes) -> bytearray:
    s = bytearray(25)
    w = BufferWriter(s, 0)
    write_op_push(w, len(signature) + 1)
    write_bytes(w, signature)
    w.writebyte(0x01)
    write_op_push(w, len(pubkey))
    write_bytes(w, pubkey)
    return


def node_derive(root: HDNode, address_n: list) -> HDNode:
    # TODO: this will probably need to be a part of the machine instructions
    node = root.clone()
    node.derive_path(address_n)
    return node


def ecdsa_get_pubkeyhash(pubkey: bytes) -> bytes:
    if pubkey[0] == 0x04:
        assert len(pubkey) == 65  # uncompressed format
    elif pubkey[0] == 0x00:
        assert len(pubkey) == 1   # point at infinity
    else:
        assert len(pubkey) == 33  # compresssed format
    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()
    return h


async def ecdsa_sign(privkey: bytes, digest: bytes) -> bytes:
    return secp256k1.sign(privkey, digest)


# TX Serialization
# ===


def tx_write_header(w, version: int, inputs_count: int):
    write_uint32(w, version)
    write_varint(w, inputs_count)


def tx_write_input(w, i: TxInputType):
    write_bytes_rev(w, i.prev_hash)
    write_uint32(w, i.prev_index)
    write_varint(w, len(i.script_sig))
    write_bytes(w, i.script_sig)
    write_uint32(w, i.sequence)


def tx_write_middle(w, outputs_count: int):
    write_varint(w, outputs_count)


def tx_write_output(w, o: TxOutputBinType):
    write_uint64(w, o.amount)
    write_varint(w, len(o.script_pubkey))
    write_bytes(w, o.script_pubkey)


def tx_write_footer(w, locktime: int, add_hash_type: bool):
    write_uint32(w, locktime)
    if add_hash_type:
        write_uint32(w, 1)


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

    def __init__(self, buf: bytearray, ofs: int):
        # TODO: re-think the use of bytearrays, buffers, and other byte IO
        # i think we should just pass a pre-allocation size here, allocate the
        # bytearray and then trim it to zero.  in this case, write() would
        # correspond to extend(), and writebyte() to append().  of course, the
        # the use-case of non-destructively writing to existing bytearray still
        # exists.
        self.buf = buf
        self.ofs = ofs

    def write(self, buf: bytearray):
        n = len(buf)
        self.buf[self.ofs:self.ofs + n] = buf
        self.ofs += n

    def writebyte(self, b: int):
        self.buf[self.ofs] = b
        self.ofs += 1

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
