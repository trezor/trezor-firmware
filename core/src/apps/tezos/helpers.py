from micropython import const

from trezor import wire
from trezor.crypto import base58
from trezor.utils import BufferReader, ensure

from apps.common.readers import read_uint32_be
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
BRANCH_HASH_SIZE = const(32)
PROPOSAL_HASH_SIZE = const(32)
PUBLIC_KEY_HASH_SIZE = const(20)
TAGGED_PUBKEY_HASH_SIZE = 1 + PUBLIC_KEY_HASH_SIZE
CONTRACT_ID_SIZE = const(22)
ED25519_PUBLIC_KEY_SIZE = const(32)
SECP256K1_PUBLIC_KEY_SIZE = const(33)
P256_PUBLIC_KEY_SIZE = const(33)

PUBLIC_KEY_TAG_TO_SIZE = {
    0: ED25519_PUBLIC_KEY_SIZE,
    1: SECP256K1_PUBLIC_KEY_SIZE,
    2: P256_PUBLIC_KEY_SIZE,
}

OP_TAG_ENDORSEMENT = const(0)
OP_TAG_SEED_NONCE_REVELATION = const(1)
OP_TAG_DOUBLE_ENDORSEMENT_EVIDENCE = const(2)
OP_TAG_DOUBLE_BAKING_EVIDENCE = const(3)
OP_TAG_ACTIVATE_ACCOUNT = const(4)
OP_TAG_PROPOSALS = const(5)
OP_TAG_BALLOT = const(6)
OP_TAG_REVEAL = const(107)
OP_TAG_TRANSACTION = const(108)
OP_TAG_ORIGINATION = const(109)
OP_TAG_DELEGATION = const(110)

EP_TAG_NAMED = const(255)


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


def write_bool(w: bytearray, boolean: bool):
    if boolean:
        write_uint8(w, 255)
    else:
        write_uint8(w, 0)


def write_instruction(w: bytearray, instruction: str) -> int:
    write_bytes_unchecked(w, MICHELSON_INSTRUCTION_BYTES[instruction])


def check_script_size(script: bytes) -> None:
    try:
        r = BufferReader(script)
        n = read_uint32_be(r)
        r.read(n)
        n = read_uint32_be(r)
        ensure(r.remaining_count() == n)
    except (AssertionError, EOFError):
        raise wire.DataError("Invalid script")


def check_tx_params_size(params: bytes) -> None:
    try:
        r = BufferReader(params)
        tag = r.get()
        if tag == EP_TAG_NAMED:
            n = r.get()
            r.read(n)
        elif tag > 4:
            raise wire.DataError("Unknown entrypoint tag")
        n = read_uint32_be(r)
        ensure(r.remaining_count() == n)
    except (AssertionError, EOFError):
        raise wire.DataError("Invalid transaction parameters")
