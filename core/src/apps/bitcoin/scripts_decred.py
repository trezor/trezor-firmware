from trezor import utils, wire
from trezor.crypto import base58
from trezor.crypto.base58 import blake256d_32

from apps.common.writers import empty_bytearray, write_bytes_fixed, write_uint64_le


# A ticket purchase submission for an address hash.
def output_script_sstxsubmissionpkh(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise wire.DataError("Invalid address")

    w = empty_bytearray(26)
    w.append(0xBA)  # OP_SSTX
    w.append(0x76)  # OP_DUP
    w.append(0xA9)  # OP_HASH160
    w.append(0x14)  # OP_DATA_20
    write_bytes_fixed(w, raw_address[2:], 20)
    w.append(0x88)  # OP_EQUALVERIFY
    w.append(0xAC)  # OP_CHECKSIG
    return w


# Ticket purchase change script.
def output_script_sstxchange(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise wire.DataError("Invalid address")

    w = empty_bytearray(26)
    w.append(0xBD)  # OP_SSTXCHANGE
    w.append(0x76)  # OP_DUP
    w.append(0xA9)  # OP_HASH160
    w.append(0x14)  # OP_DATA_20
    write_bytes_fixed(w, raw_address[2:], 20)
    w.append(0x88)  # OP_EQUALVERIFY
    w.append(0xAC)  # OP_CHECKSIG
    return w


# Spend from a stake revocation.
def output_script_ssrtx(pkh: bytes) -> bytearray:
    utils.ensure(len(pkh) == 20)
    s = bytearray(26)
    s[0] = 0xBC  # OP_SSRTX
    s[1] = 0x76  # OP_DUP
    s[2] = 0xA9  # OP_HASH160
    s[3] = 0x14  # OP_DATA_20
    s[4:24] = pkh
    s[24] = 0x88  # OP_EQUALVERIFY
    s[25] = 0xAC  # OP_CHECKSIG
    return s


# Spend from a stake generation.
def output_script_ssgen(pkh: bytes) -> bytearray:
    utils.ensure(len(pkh) == 20)
    s = bytearray(26)
    s[0] = 0xBB  # OP_SSGEN
    s[1] = 0x76  # OP_DUP
    s[2] = 0xA9  # OP_HASH160
    s[3] = 0x14  # OP_DATA_20
    s[4:24] = pkh
    s[24] = 0x88  # OP_EQUALVERIFY
    s[25] = 0xAC  # OP_CHECKSIG
    return s


# Retrieve pkh bytes from a stake commitment OPRETURN.
def sstxcommitment_pkh(pkh: bytes, amount: int) -> bytes:
    w = empty_bytearray(30)
    write_bytes_fixed(w, pkh, 20)
    write_uint64_le(w, amount)
    write_bytes_fixed(w, b"\x00\x58", 2)  # standard fee limits
    return w
