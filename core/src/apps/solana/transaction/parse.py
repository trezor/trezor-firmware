from typing import TYPE_CHECKING

from apps.common.readers import read_uint64_le

if TYPE_CHECKING:
    from trezor.utils import BufferReader


def parse_var_int(serialized_tx: BufferReader) -> int:
    # Compact-u16 as decoded by solana-sdk's short_vec::visit_byte():
    # https://github.com/anza-xyz/solana-sdk/blob/e2adabb20e084efe4e5a872bb5be71051130bcd8/short-vec/src/lib.rs#L104-L133
    value = 0
    for i in range(3):
        B = serialized_tx.get()  # raises EOFError if truncated
        if B == 0 and i != 0:
            raise ValueError  # alias (non-canonical encoding)
        value |= (B & 0b01111111) << (7 * i)
        if B & 0b10000000 == 0:
            break
    else:
        raise ValueError  # the third byte must be the last one

    if value > 0xFFFF:
        raise ValueError  # compact-u16 value too large

    return value


def parse_block_hash(serialized_tx: BufferReader) -> bytes:
    return bytes(serialized_tx.read_memoryview(32))


def parse_pubkey(serialized_tx: BufferReader) -> bytes:
    return bytes(serialized_tx.read_memoryview(32))


def parse_enum(serialized_tx: BufferReader) -> int:
    return serialized_tx.get()


def parse_string(serialized_tx: BufferReader) -> str:
    # TODO SOL: validation shall be checked (length is less than 2^32 or even less)
    length = read_uint64_le(serialized_tx)
    return bytes(serialized_tx.read_memoryview(length)).decode("utf-8")


def parse_memo(serialized_tx: BufferReader) -> str:
    return bytes(serialized_tx.read_memoryview(serialized_tx.remaining_count())).decode(
        "utf-8"
    )


def parse_byte(serialized_tx: BufferReader) -> int:
    return serialized_tx.get()
