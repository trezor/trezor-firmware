from trezor.crypto.hashlib import sha256
from trezor.crypto import HDNode
from trezor.utils import memcpy, memcpy_rev

from . import coins
from . import seed

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

        for i in range(tx.inputs_count):
            # STAGE_REQUEST_4_INPUT
            input = await request_tx_input(i)
            tx_write_input(h_second, input)
            if i == i_sign:
                signing_key = node_derive(root, input.address_n)
                signing_key_pub = signing_key.public_key()
                input.script_sig = input_derive_scriptsig_for_signing(
                    input, signing_key_pub)
            else:
                input.script_sig = bytes()
            tx_write_input(h_sign, input)

        for o in range(tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT
            output = await request_tx_output(o)
            outputbin = output_compile(output, coin, root)
            tx_write_output(h_second, outputbin)
            tx_write_output(h_sign, outputbin)

        if h_first_dig != tx_hash_digest(h_second):
            raise ValueError('Transaction has changed during signing')

        sig = sign(signing_key, tx_hash_digest(h_sign))
        # TODO: serialize scriptsig again
        # TODO: serialize input
        serialized = xxx
        await send_serialized_tx(serialized)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_5_OUTPUT
        output = await request_tx_output(o)
        outputbin = output_compile(output, coin, root)
        serialized = xxx
        await send_serialized_tx(serialized)

    await request_tx_finish()


async def get_prevtx_output_value(prev_hash: bytes, prev_index: int) -> int:

    total_in = 0

    # STAGE_REQUEST_2_PREV_META
    tx = await TxRequest(type=TXMETA, hash=prev_hash)

    h = tx_hash_init()
    tx_write_header(h, tx.version, tx.inputs_count)

    for i in range(tx.inputs_count):
        # STAGE_REQUEST_2_PREV_INPUT
        input = await TxRequest(type=TXINPUT, hash=prev_hash, index=i)
        tx_write_input(h, input)

    tx_write_middle(h, tx.outputs_count)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_2_PREV_OUTPUT
        outputbin = await TxRequest(type=TXOUTPUT, hash=prev_hash, index=o)
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

    if output.script_type == OutputScriptType.PAYTOADDRESS:
        raw_address = output_paytoaddress_extract_raw_address(output, root)
        if raw_address[0] != coin.address_type:
            raise ValueError('Invalid address type')
        bin.script_pubkey = script_paytoaddress_new(raw_address)

    else:
        # TODO: other output script types
        raise ValueError('Unknown output script type')

    return bin


def output_paytoaddress_extract_raw_address(output: TxOutputType, root: HDNode) -> bytes:
    output_address_n = getattr(output, 'address_n', None)
    output_address = getattr(output, 'address_n', None)
    if output_address_n:
        node = node_derive(root, output_address_n)
        # TODO: dont encode and decode again
        raw_address = address_decode(node.address())
    elif output_address:
        raw_address = address_decode(output_address)
    else:
        raise ValueError('Missing address')
    return raw_address


def script_paytoaddress_new(raw_address: bytes) -> bytearray:
    s = bytearray(25)
    s[0] = 0x76  # OP_DUP
    s[1] = 0xA9  # OP_HASH_160
    s[2] = 0x14  # pushing 20 bytes
    s[3:23] = raw_address
    s[23] = 0x88  # OP_EQUALVERIFY
    s[24] = 0xAC  # OP_CHECKSIG
    return s


def output_is_change(output: TxOutputType):
    address_n = getattr(output, 'address_n', None)
    return bool(address_n)


# Tx Inputs
# ===


def input_derive_scriptsig_for_signing(input: TxInputType, pubkey: bytes) -> bytes:
    if input.script_type == InputScriptType.SPENDADDRESS:
        pubkeyhash = xxx
        return script_spendaddress_new(pubkeyhash)

    else:
        # TODO: other input script types
        raise ValueError('Unknown input script type')


def script_spendaddress_new(pubkeyhash: bytes) -> bytearray:
    s = bytearray(25)
    s[0] = 0x76  # OP_DUP
    s[1] = 0xA9  # OP_HASH_160
    s[2] = 0x14  # pushing 20 bytes
    s[3:23] = pubkeyhash
    s[23] = 0x88  # OP_EQUALVERIFY
    s[24] = 0xAC  # OP_CHECKSIG
    return s


async def sign(privkey: bytes, digest: bytes) -> bytes:
    # TODO: ecdsa secp256k1 digest sign
    return b''


# Addresses, HDNodes
# ===


def node_derive(root: HDNode, address_n: list) -> HDNode:
    # TODO: this will probably need to be a part of the machine instructions
    node = root.clone()
    node.derive_path(address_n)
    return node


def address_decode(address: str) -> bytes:
    # TODO: decode the address from base58
    return b''


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


# Buffer IO & Serialization
# ===


def write_varint(w, n: int):
    wb = w.writebyte
    if n < 253:
        wb(n & 0xFF)
    elif n < 0x10000:
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
        self.buf = buf
        self.ofs = ofs

    def write(self, buf):
        n = len(buf)
        w = memcpy(self.buf, self.ofs, buf, 0, n)
        self.ofs += w
        return w

    def writebyte(self, b):
        self.buf[self.ofs] = b
        self.ofs += 1

    def getvalue(self):
        return self.buf


class HashWriter:

    def __init__(self, hashfunc):
        self.ctx = hashfunc()

    def write(self, buf):
        self.ctx.update(buf)

    def writebyte(self, b):
        self.ctx.update(bytes(b))

    def getvalue(self):
        return self.ctx.digest()
