# Serializes into the Ripple Format
#
# Inspired by https://github.com/miracle2k/ripple-python and https://github.com/ripple/ripple-lib
# Docs at https://wiki.ripple.com/Binary_Format and https://developers.ripple.com/transaction-common-fields.html
#
# The first four bits specify the field type (int16, int32, account..)
# the other four the record type (amount, fee, destination..) and then
# the actual data follow. This currently only supports the Payment
# transaction type and the fields that are required for it.
#
from trezor.messages.RippleSignTx import RippleSignTx

from . import helpers

FIELD_TYPE_INT16 = 1
FIELD_TYPE_INT32 = 2
FIELD_TYPE_AMOUNT = 6
FIELD_TYPE_VL = 7
FIELD_TYPE_ACCOUNT = 8

FIELDS_MAP = {
    "account": {"type": FIELD_TYPE_ACCOUNT, "key": 1},
    "amount": {"type": FIELD_TYPE_AMOUNT, "key": 1},
    "destination": {"type": FIELD_TYPE_ACCOUNT, "key": 3},
    "fee": {"type": FIELD_TYPE_AMOUNT, "key": 8},
    "sequence": {"type": FIELD_TYPE_INT32, "key": 4},
    "type": {"type": FIELD_TYPE_INT16, "key": 2},
    "signingPubKey": {"type": FIELD_TYPE_VL, "key": 3},
    "flags": {"type": FIELD_TYPE_INT32, "key": 2},
    "txnSignature": {"type": FIELD_TYPE_VL, "key": 4},
    "lastLedgerSequence": {"type": FIELD_TYPE_INT32, "key": 27},
}

TRANSACTION_TYPES = {"Payment": 0}


def serialize(msg: RippleSignTx, source_address: str, pubkey=None, signature=None):
    w = bytearray()
    # must be sorted numerically first by type and then by name
    write(w, FIELDS_MAP["type"], TRANSACTION_TYPES["Payment"])
    write(w, FIELDS_MAP["flags"], msg.flags)
    write(w, FIELDS_MAP["sequence"], msg.sequence)
    write(w, FIELDS_MAP["lastLedgerSequence"], msg.last_ledger_sequence)
    write(w, FIELDS_MAP["amount"], msg.payment.amount)
    write(w, FIELDS_MAP["fee"], msg.fee)
    write(w, FIELDS_MAP["signingPubKey"], pubkey)
    write(w, FIELDS_MAP["txnSignature"], signature)
    write(w, FIELDS_MAP["account"], source_address)
    write(w, FIELDS_MAP["destination"], msg.payment.destination)
    return w


def write(w: bytearray, field: dict, value):
    if value is None:
        return
    write_type(w, field)
    if field["type"] == FIELD_TYPE_INT16:
        w.extend(value.to_bytes(2, "big"))
    elif field["type"] == FIELD_TYPE_INT32:
        w.extend(value.to_bytes(4, "big"))
    elif field["type"] == FIELD_TYPE_AMOUNT:
        w.extend(serialize_amount(value))
    elif field["type"] == FIELD_TYPE_ACCOUNT:
        write_bytes(w, helpers.decode_address(value))
    elif field["type"] == FIELD_TYPE_VL:
        write_bytes(w, value)
    else:
        raise ValueError("Unknown field type")


def write_type(w: bytearray, field: dict):
    if field["key"] <= 0xf:
        w.append((field["type"] << 4) | field["key"])
    else:
        # this concerns two-bytes fields such as lastLedgerSequence
        w.append(field["type"] << 4)
        w.append(field["key"])


def serialize_amount(value: int) -> bytearray:
    if value < 0 or isinstance(value, float):
        raise ValueError("Only positive integers are supported")
    if value > 100000000000:  # max allowed value
        raise ValueError("Value is larger than 100000000000")

    b = bytearray(value.to_bytes(8, "big"))
    # Clear first bit to indicate XRP
    b[0] &= 0x7f
    # Set second bit to indicate positive number
    b[0] |= 0x40
    return b


def write_bytes(w: bytearray, value: bytes):
    """Serialize a variable length bytes."""
    serialize_varint(w, len(value))
    w.extend(value)


def serialize_varint(w, val):
    """https://ripple.com/wiki/Binary_Format#Variable_Length_Data_Encoding"""

    def rshift(val, n):
        # http://stackoverflow.com/a/5833119/15677
        return (val % 0x100000000) >> n

    assert val >= 0

    b = bytearray()
    if val < 192:
        b.append(val)
    elif val <= 12480:
        val -= 193
        b.extend([193 + rshift(val, 8), val & 0xff])
    elif val <= 918744:
        val -= 12481
        b.extend([241 + rshift(val, 16), rshift(val, 8) & 0xff, val & 0xff])
    else:
        raise ValueError("Variable integer overflow.")

    w.extend(b)
