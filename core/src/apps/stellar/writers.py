from .helpers import public_key_from_address

from apps.common.writers import write_bytes, write_uint32_be, write_uint64_be

write_uint32 = write_uint32_be
write_uint64 = write_uint64_be


def write_string(w, s: str):
    buf = s.encode()
    write_uint32(w, len(buf))
    write_bytes(w, buf)
    # if len isn't a multiple of 4, add padding bytes
    reminder = len(buf) % 4
    if reminder:
        write_bytes(w, bytes([0] * (4 - reminder)))


def write_bool(w, val: bool):
    if val:
        write_uint32(w, 1)
    else:
        write_uint32(w, 0)


def write_pubkey(w, address: str):
    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    write_bytes(w, public_key_from_address(address))
