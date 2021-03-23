from micropython import const

from trezor.crypto.hashlib import sha256
from trezor.utils import ensure

from apps.common.writers import (  # noqa: F401
    write_bitcoin_varint,
    write_bytes_fixed,
    write_bytes_reversed,
    write_bytes_unchecked,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le,
)

if False:
    from trezor.messages import (
        PrevInput,
        PrevOutput,
        TxInput,
        TxOutput,
    )
    from trezor.utils import HashWriter

    from apps.common.writers import Writer

write_uint16 = write_uint16_le
write_uint32 = write_uint32_le
write_uint64 = write_uint64_le

TX_HASH_SIZE = const(32)


def write_bytes_prefixed(w: Writer, b: bytes) -> None:
    write_bitcoin_varint(w, len(b))
    write_bytes_unchecked(w, b)


def write_tx_input(w: Writer, i: TxInput | PrevInput, script: bytes) -> None:
    write_bytes_reversed(w, i.prev_hash, TX_HASH_SIZE)
    write_uint32(w, i.prev_index)
    write_bytes_prefixed(w, script)
    write_uint32(w, i.sequence)


def write_tx_input_check(w: Writer, i: TxInput) -> None:
    write_bytes_fixed(w, i.prev_hash, TX_HASH_SIZE)
    write_uint32(w, i.prev_index)
    write_uint32(w, i.script_type)
    write_uint32(w, len(i.address_n))
    for n in i.address_n:
        write_uint32(w, n)
    write_uint32(w, i.sequence)
    write_uint64(w, i.amount or 0)


def write_tx_output(w: Writer, o: TxOutput | PrevOutput, script_pubkey: bytes) -> None:
    write_uint64(w, o.amount)
    write_bytes_prefixed(w, script_pubkey)


def write_op_push(w: Writer, n: int) -> None:
    ensure(n >= 0 and n <= 0xFFFF_FFFF)
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


def get_tx_hash(w: HashWriter, double: bool = False, reverse: bool = False) -> bytes:
    d = w.get_digest()
    if double:
        d = sha256(d).digest()
    if reverse:
        d = bytes(reversed(d))
    return d
