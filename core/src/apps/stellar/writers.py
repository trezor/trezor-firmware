from micropython import const
from typing import TYPE_CHECKING

import apps.common.writers as writers

# Reexporting to other modules
write_bytes_fixed = writers.write_bytes_fixed
write_bytes_unchecked = writers.write_bytes_unchecked
write_uint32 = writers.write_uint32_be
write_uint64 = writers.write_uint64_be

if TYPE_CHECKING:
    from buffer_types import StrOrBytes

    from trezor.utils import Writer


def write_string(w: Writer, s: StrOrBytes) -> int:
    """Write XDR string padded to a multiple of 4 bytes.
    Returns the length of the string written to the buffer (without padding).
    """
    # NOTE: 2 bytes smaller than if-else
    buf = s.encode() if isinstance(s, str) else s
    write_uint32(w, len(buf))
    writers.write_bytes_unchecked(w, buf)
    # if len isn't a multiple of 4, add padding bytes
    remainder = len(buf) % 4
    if remainder:
        writers.write_bytes_unchecked(w, bytes([0] * (4 - remainder)))
    return len(buf)


def write_bool(w: Writer, val: bool) -> None:
    # NOTE: 10 bytes smaller than if-else
    write_uint32(w, 1 if val else 0)


def write_pubkey(w: Writer, address: str) -> None:
    from .helpers import public_key_from_address

    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    writers.write_bytes_fixed(w, public_key_from_address(address), 32)


_INT32_MIN = const(-0x8000_0000)
_INT32_MAX = const(0x7FFF_FFFF)
_UINT32_MASK = const(0xFFFF_FFFF)

_INT64_MIN = const(-0x8000_0000_0000_0000)
_INT64_MAX = const(0x7FFF_FFFF_FFFF_FFFF)
_UINT64_MASK = const(0xFFFF_FFFF_FFFF_FFFF)


def write_int32(w: Writer, value: int) -> None:
    """Write signed 32-bit integer in big-endian."""
    if value < _INT32_MIN or value > _INT32_MAX:
        raise ValueError("int32 out of range")
    write_uint32(w, value & _UINT32_MASK)


def write_int64(w: Writer, value: int) -> None:
    """Write signed 64-bit integer in big-endian."""
    if value < _INT64_MIN or value > _INT64_MAX:
        raise ValueError("int64 out of range")
    write_uint64(w, value & _UINT64_MASK)
