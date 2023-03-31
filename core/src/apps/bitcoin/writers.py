from micropython import const
from typing import TYPE_CHECKING

from trezor.utils import ensure

from apps.common.writers import (  # noqa: F401
    write_bytes_fixed,
    write_bytes_reversed,
    write_bytes_unchecked,
    write_compact_size,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le,
)

if TYPE_CHECKING:
    from trezor.messages import PrevInput, PrevOutput, TxInput, TxOutput
    from trezor.utils import HashWriter

    from apps.common.writers import Writer

write_uint16 = write_uint16_le
write_uint32 = write_uint32_le
write_uint64 = write_uint64_le

TX_HASH_SIZE = const(32)


def write_bytes_prefixed(w: Writer, b: bytes) -> None:
    write_compact_size(w, len(b))
    write_bytes_unchecked(w, b)


def write_tx_input(w: Writer, i: TxInput | PrevInput, script: bytes) -> None:
    write_bytes_reversed(w, i.prev_hash, TX_HASH_SIZE)
    write_uint32(w, i.prev_index)
    write_bytes_prefixed(w, script)
    write_uint32(w, i.sequence)


def write_tx_input_check(w: Writer, i: TxInput) -> None:
    from .multisig import multisig_fingerprint

    write_uint32(w, len(i.address_n))
    for n in i.address_n:
        write_uint32(w, n)
    write_bytes_fixed(w, i.prev_hash, TX_HASH_SIZE)
    write_uint32(w, i.prev_index)
    write_bytes_prefixed(w, i.script_sig or b"")
    write_uint32(w, i.sequence)
    write_uint32(w, i.script_type)
    multisig_fp = multisig_fingerprint(i.multisig) if i.multisig else b""
    write_bytes_prefixed(w, multisig_fp)
    write_uint64(w, i.amount or 0)
    write_bytes_prefixed(w, i.witness or b"")
    write_bytes_prefixed(w, i.ownership_proof or b"")
    write_bytes_prefixed(w, i.orig_hash or b"")
    write_uint32(w, i.orig_index or 0)
    write_bytes_prefixed(w, i.script_pubkey or b"")


def write_tx_output(w: Writer, o: TxOutput | PrevOutput, script_pubkey: bytes) -> None:
    write_uint64(w, o.amount)
    write_bytes_prefixed(w, script_pubkey)


def write_op_push(w: Writer, n: int) -> None:
    append = w.append  # local_cache_attribute

    ensure(0 <= n <= 0xFFFF_FFFF)
    if n < 0x4C:
        append(n & 0xFF)
    elif n < 0x100:
        append(0x4C)
        append(n & 0xFF)
    elif n < 0x1_0000:
        append(0x4D)
        append(n & 0xFF)
        append((n >> 8) & 0xFF)
    else:
        append(0x4E)
        append(n & 0xFF)
        append((n >> 8) & 0xFF)
        append((n >> 16) & 0xFF)
        append((n >> 24) & 0xFF)


def op_push_length(n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF)
    if n < 0x4C:
        return 1
    elif n < 0x100:
        return 2
    elif n < 0x1_0000:
        return 3
    else:
        return 4


def get_tx_hash(w: HashWriter, double: bool = False, reverse: bool = False) -> bytes:
    from trezor.crypto.hashlib import sha256

    d = w.get_digest()
    if double:
        d = sha256(d).digest()
    if reverse:
        d = bytes(reversed(d))
    return d
