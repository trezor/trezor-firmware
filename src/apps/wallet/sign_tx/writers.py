from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxInputType import TxInputType
from trezor.crypto.hashlib import sha256

# TX Serialization
# ===

_DEFAULT_SEQUENCE = 4294967295


def write_tx_input(w, i: TxInputType):
    i_sequence = i.sequence if i.sequence is not None else _DEFAULT_SEQUENCE
    write_bytes_rev(w, i.prev_hash)
    write_uint32(w, i.prev_index)
    write_varint(w, len(i.script_sig))
    write_bytes(w, i.script_sig)
    write_uint32(w, i_sequence)


def write_tx_input_check(w, i: TxInputType):
    i_sequence = i.sequence if i.sequence is not None else _DEFAULT_SEQUENCE
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
    if n < 0x4C:
        w.append(n & 0xFF)
    elif n < 0xFF:
        w.append(0x4C)
        w.append(n & 0xFF)
    elif n < 0xFFFF:
        w.append(0x4D)
        w.append(n & 0xFF)
        w.append((n >> 8) & 0xFF)
    else:
        w.append(0x4E)
        w.append(n & 0xFF)
        w.append((n >> 8) & 0xFF)
        w.append((n >> 16) & 0xFF)
        w.append((n >> 24) & 0xFF)


# Buffer IO & Serialization
# ===


def write_varint(w, n: int):
    if n < 253:
        w.append(n & 0xFF)
    elif n < 65536:
        w.append(253)
        w.append(n & 0xFF)
        w.append((n >> 8) & 0xFF)
    else:
        w.append(254)
        w.append(n & 0xFF)
        w.append((n >> 8) & 0xFF)
        w.append((n >> 16) & 0xFF)
        w.append((n >> 24) & 0xFF)


def write_uint32(w, n: int):
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)


def write_uint64(w, n: int):
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 32) & 0xFF)
    w.append((n >> 40) & 0xFF)
    w.append((n >> 48) & 0xFF)
    w.append((n >> 56) & 0xFF)


def write_bytes(w, buf: bytearray):
    w.extend(buf)


def write_bytes_rev(w, buf: bytearray):
    w.extend(bytearray(reversed(buf)))


def bytearray_with_cap(cap: int) -> bytearray:
    b = bytearray(cap)
    b[:] = bytes()
    return b


# Hashes
# ===


def get_tx_hash(w, double: bool, reverse: bool=False) -> bytes:
    d = w.getvalue()
    if double:
        d = sha256(d).digest()
    if reverse:
        d = bytes(reversed(d))
    return d


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
