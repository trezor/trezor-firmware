from typing import TYPE_CHECKING

import apps.common.writers as writers

# Reexporting to other modules
write_bytes_fixed = writers.write_bytes_fixed
write_uint32 = writers.write_uint32_be
write_uint64 = writers.write_uint64_be

if TYPE_CHECKING:
    from typing import AnyStr

    from trezor.utils import Writer


def write_string(w: Writer, s: AnyStr) -> None:
    """Write XDR string padded to a multiple of 4 bytes."""
    # NOTE: 2 bytes smaller than if-else
    buf = s.encode() if isinstance(s, str) else s
    write_uint32(w, len(buf))
    writers.write_bytes_unchecked(w, buf)
    # if len isn't a multiple of 4, add padding bytes
    remainder = len(buf) % 4
    if remainder:
        writers.write_bytes_unchecked(w, bytes([0] * (4 - remainder)))


def write_bool(w: Writer, val: bool) -> None:
    # NOTE: 10 bytes smaller than if-else
    write_uint32(w, 1 if val else 0)


def write_pubkey(w: Writer, address: str) -> None:
    from .helpers import public_key_from_address

    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    writers.write_bytes_fixed(w, public_key_from_address(address), 32)
