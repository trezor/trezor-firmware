from micropython import const

from trezor.crypto import base58

from apps.common import HARDENED
from apps.common.writers import write_bytes_unchecked, write_uint8

TEZOS_AMOUNT_DECIMALS = const(6)
TEZOS_ED25519_ADDRESS_PREFIX = "tz1"
TEZOS_ORIGINATED_ADDRESS_PREFIX = "KT1"
TEZOS_PUBLICKEY_PREFIX = "edpk"
TEZOS_SIGNATURE_PREFIX = "edsig"
TEZOS_PREFIX_BYTES = {
    # addresses
    "tz1": b"\x06\xa1\x9f",  # 06a19f
    "tz2": b"\x06\xa1\xa1",  # 06a1a1
    "tz3": b"\x06\xa1\xa4",  # 06a1a4
    "KT1": b"\x02Zy",  # 025a79
    # public keys
    "edpk": b"\r\x0f%\xd9",  # 0d0f25d9
    # signatures
    "edsig": b"\t\xf5\xcd\x86\x12",  # 09f5cd8612
    # operation hash
    "o": b"\x05t",  # 0574
    # protocol hash
    "P": b"\x02\xaa",  # 02aa
}

MICHELSON_INSTRUCTION_BYTES = {
    "DROP": b"\x03 ",  # 0320
    "NIL": b"\x05=",  # 053d
    "operation": b"\x03m",  # 036d
    "NONE": b"\x05>",  # 053e
    "key_hash": b"\x03]",  # 035d
    "SET_DELEGATE": b"\x03N",  # 034e
    "CONS": b"\x03\x1b",  # 031b
    "IMPLICIT_ACCOUNT": b"\x03\x1e",  # 031e
    "PUSH": b"\x07C",  # 0743
    "mutez": b"\x03j",  # 036a
    "UNIT": b"\x03O",  # 034f
    "TRANSFER_TOKENS": b"\x03M",  # 034d
    "SOME": b"\x03F",  # 0346
    "address": b"\x03n",  # 036e
    "CONTRACT": b"\x05U",  # 0555
    "unit": b"\x03l",  # 036c
    # ASSERT_SOME unfolded as { IF_NONE { { UNIT ; FAILWITH } } {} }
    # 0200000015072f02000000090200000004034f03270200000000
    "ASSERT_SOME": b"\x02\x00\x00\x00\x15\x07/\x02\x00\x00\x00\t\x02\x00\x00\x00\x04\x03O\x03'\x02\x00\x00\x00\x00",
}

DO_ENTRYPOINT_TAG = const(2)
MICHELSON_SEQUENCE_TAG = const(2)


def base58_encode_check(payload, prefix=None):
    result = payload
    if prefix is not None:
        result = TEZOS_PREFIX_BYTES[prefix] + payload
    return base58.encode_check(result)


def base58_decode_check(enc, prefix=None):
    decoded = base58.decode_check(enc)
    if prefix is not None:
        decoded = decoded[len(TEZOS_PREFIX_BYTES[prefix]) :]
    return decoded


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/1729'/a',
    where `a` is an account index from 0 to 1 000 000.
    Additional component added to allow ledger migration
    44'/1729'/0'/b' where `b` is an account index from 0 to 1 000 000
    """
    length = len(path)
    if length < 3 or length > 4:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 1729 | HARDENED:
        return False
    if length == 3:
        if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
            return False
    if length == 4:
        if path[2] != 0 | HARDENED:
            return False
        if path[3] < HARDENED or path[3] > 1000000 | HARDENED:
            return False
    return True


def write_bool(w: bytearray, boolean: bool):
    if boolean:
        write_uint8(w, 255)
    else:
        write_uint8(w, 0)


def write_instruction(w: bytearray, instruction: str) -> int:
    write_bytes_unchecked(w, MICHELSON_INSTRUCTION_BYTES[instruction])
