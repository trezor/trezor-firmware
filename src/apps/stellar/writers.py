import ustruct

from .helpers import public_key_from_address


def write_uint32(w, n: int):
    write_bytes(w, ustruct.pack(">L", n))


def write_uint64(w, n: int):
    write_bytes(w, ustruct.pack(">Q", n))


def write_string(w, s: str):
    write_uint32(w, len(s))
    write_bytes(w, bytearray(s))
    # if len isn't a multiple of 4, add padding bytes
    reminder = len(s) % 4
    if reminder:
        write_bytes(w, bytearray([0] * (4 - reminder)))


def write_bytes(w, buf: bytearray):
    w.extend(buf)


def write_bool(w, val: True):
    if val:
        write_uint32(w, 1)
    else:
        write_uint32(w, 0)


def write_pubkey(w, address: str):
    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    pubkey = public_key_from_address(address)
    write_bytes(w, bytearray(pubkey))
