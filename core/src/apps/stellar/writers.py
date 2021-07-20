from apps.common.writers import (
    write_bytes_fixed,
    write_bytes_unchecked,
    write_uint32_be,
    write_uint64_be,
)

from .helpers import public_key_from_address

write_uint32 = write_uint32_be
write_uint64 = write_uint64_be

if False:
    from typing import AnyStr

    from trezor.utils import Writer


def write_string(w: Writer, s: AnyStr) -> None:
    """Write XDR string padded to a multiple of 4 bytes."""
    if isinstance(s, str):
        buf = s.encode()
    else:
        buf = s
    write_uint32(w, len(buf))
    write_bytes_unchecked(w, buf)
    # if len isn't a multiple of 4, add padding bytes
    remainder = len(buf) % 4
    if remainder:
        write_bytes_unchecked(w, bytes([0] * (4 - remainder)))


def write_bool(w: Writer, val: bool) -> None:
    if val:
        write_uint32(w, 1)
    else:
        write_uint32(w, 0)


def write_pubkey(w: Writer, address: str) -> None:
    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    write_bytes_fixed(w, public_key_from_address(address), 32)
