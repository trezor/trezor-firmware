# Serializes into the Ripple Format
#
# Inspired by https://github.com/miracle2k/ripple-python and https://github.com/ripple/ripple-lib
# Docs at https://wiki.ripple.com/Binary_Format and https://developers.ripple.com/transaction-common-fields.html
#
# The first four bits specify the field type (int16, int32, account..)
# the other four the record type (amount, fee, destination..) and then
# the actual data follow. This currently only supports the Payment
# transaction type and the fields that are required for it.

from typing import TYPE_CHECKING

from trezor.messages import RippleSignTx

from . import helpers

if TYPE_CHECKING:
    from trezor.utils import Writer


class RippleField:
    def __init__(self, type: int, key: int) -> None:
        self.type: int = type
        self.key: int = key


FIELD_TYPE_INT16 = 1
FIELD_TYPE_INT32 = 2
FIELD_TYPE_AMOUNT = 6
FIELD_TYPE_VL = 7
FIELD_TYPE_ACCOUNT = 8

FIELDS_MAP: dict[str, RippleField] = {
    "account": RippleField(type=FIELD_TYPE_ACCOUNT, key=1),
    "amount": RippleField(type=FIELD_TYPE_AMOUNT, key=1),
    "destination": RippleField(type=FIELD_TYPE_ACCOUNT, key=3),
    "fee": RippleField(type=FIELD_TYPE_AMOUNT, key=8),
    "sequence": RippleField(type=FIELD_TYPE_INT32, key=4),
    "type": RippleField(type=FIELD_TYPE_INT16, key=2),
    "signingPubKey": RippleField(type=FIELD_TYPE_VL, key=3),
    "flags": RippleField(type=FIELD_TYPE_INT32, key=2),
    "txnSignature": RippleField(type=FIELD_TYPE_VL, key=4),
    "lastLedgerSequence": RippleField(type=FIELD_TYPE_INT32, key=27),
    "destinationTag": RippleField(type=FIELD_TYPE_INT32, key=14),
}

TRANSACTION_TYPES = {"Payment": 0}


def serialize(
    msg: RippleSignTx,
    source_address: str,
    pubkey: bytes,
    signature: bytes | None = None,
) -> bytearray:
    w = bytearray()
    # must be sorted numerically first by type and then by name
    write(w, FIELDS_MAP["type"], TRANSACTION_TYPES["Payment"])
    write(w, FIELDS_MAP["flags"], msg.flags)
    write(w, FIELDS_MAP["sequence"], msg.sequence)
    write(w, FIELDS_MAP["destinationTag"], msg.payment.destination_tag)
    write(w, FIELDS_MAP["lastLedgerSequence"], msg.last_ledger_sequence)
    write(w, FIELDS_MAP["amount"], msg.payment.amount)
    write(w, FIELDS_MAP["fee"], msg.fee)
    write(w, FIELDS_MAP["signingPubKey"], pubkey)
    write(w, FIELDS_MAP["txnSignature"], signature)
    write(w, FIELDS_MAP["account"], source_address)
    write(w, FIELDS_MAP["destination"], msg.payment.destination)
    return w


def write(w: Writer, field: RippleField, value: int | bytes | str | None) -> None:
    if value is None:
        return
    write_type(w, field)
    if field.type == FIELD_TYPE_INT16:
        assert isinstance(value, int)
        w.extend(value.to_bytes(2, "big"))
    elif field.type == FIELD_TYPE_INT32:
        assert isinstance(value, int)
        w.extend(value.to_bytes(4, "big"))
    elif field.type == FIELD_TYPE_AMOUNT:
        assert isinstance(value, int)
        w.extend(serialize_amount(value))
    elif field.type == FIELD_TYPE_ACCOUNT:
        assert isinstance(value, str)
        write_bytes_varint(w, helpers.decode_address(value))
    elif field.type == FIELD_TYPE_VL:
        assert isinstance(value, (bytes, bytearray))
        write_bytes_varint(w, value)
    else:
        raise ValueError("Unknown field type")


def write_type(w: Writer, field: RippleField) -> None:
    if field.key <= 0xF:
        w.append((field.type << 4) | field.key)
    else:
        # this concerns two-bytes fields such as lastLedgerSequence
        w.append(field.type << 4)
        w.append(field.key)


def serialize_amount(value: int) -> bytearray:
    if value < 0:
        raise ValueError("Only non-negative integers are supported")
    if value > helpers.MAX_ALLOWED_AMOUNT:
        raise ValueError("Value is too large")

    b = bytearray(value.to_bytes(8, "big"))
    b[0] &= 0x7F  # clear first bit to indicate XRP
    b[0] |= 0x40  # set second bit to indicate positive number
    return b


def write_bytes_varint(w: Writer, value: bytes) -> None:
    """Serialize a variable length bytes."""
    write_varint(w, len(value))
    w.extend(value)


def write_varint(w: Writer, val: int) -> None:
    """
    Implements variable-length int encoding from Ripple.
    See: https://ripple.com/wiki/Binary_Format#Variable_Length_Data_Encoding
    """
    if val < 0:
        raise ValueError("Only non-negative integers are supported")
    elif val < 192:
        w.append(val)
    elif val <= 12480:
        val -= 193
        w.append(193 + rshift(val, 8))
        w.append(val & 0xFF)
    elif val <= 918744:
        val -= 12481
        w.append(241 + rshift(val, 16))
        w.append(rshift(val, 8) & 0xFF)
        w.append(val & 0xFF)
    else:
        raise ValueError("Value is too large")


def rshift(val: int, n: int) -> int:
    """
    Implements signed right-shift.
    See: http://stackoverflow.com/a/5833119/15677
    """
    return (val % 0x1_0000_0000) >> n
