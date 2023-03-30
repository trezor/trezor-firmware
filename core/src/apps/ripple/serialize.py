# Serializes into the Ripple Format
#
# Inspired by https://github.com/miracle2k/ripple-python and https://github.com/ripple/ripple-lib
# Docs at https://wiki.ripple.com/Binary_Format and https://developers.ripple.com/transaction-common-fields.html
#
# The first four bits specify the field type (int16, int32, account..)
# the other four the record type (amount, fee, destination..) and then
# the actual data follow. This currently only supports the Payment
# transaction type and the fields that are required for it.

from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import RippleSignTx
    from trezor.utils import Writer


_FIELD_TYPE_INT16 = const(1)
_FIELD_TYPE_INT32 = const(2)
_FIELD_TYPE_AMOUNT = const(6)
_FIELD_TYPE_VL = const(7)
_FIELD_TYPE_ACCOUNT = const(8)


def serialize(
    msg: RippleSignTx,
    source_address: str,
    pubkey: bytes,
    signature: bytes | None = None,
) -> bytearray:
    # must be sorted numerically first by type and then by name
    fields_to_write = (  # field_type, field_key, value
        (_FIELD_TYPE_INT16, 2, 0),  # payment type is 0
        (_FIELD_TYPE_INT32, 2, msg.flags),  # flags
        (_FIELD_TYPE_INT32, 4, msg.sequence),  # sequence
        (_FIELD_TYPE_INT32, 14, msg.payment.destination_tag),  # destinationTag
        (_FIELD_TYPE_INT32, 27, msg.last_ledger_sequence),  # lastLedgerSequence
        (_FIELD_TYPE_AMOUNT, 1, msg.payment.amount),  # amount
        (_FIELD_TYPE_AMOUNT, 8, msg.fee),  # fee
        (_FIELD_TYPE_VL, 3, pubkey),  # signingPubKey
        (_FIELD_TYPE_VL, 4, signature),  # txnSignature
        (_FIELD_TYPE_ACCOUNT, 1, source_address),  # account
        (_FIELD_TYPE_ACCOUNT, 3, msg.payment.destination),  # destination
    )

    w = bytearray()
    for field_type, field_key, value in fields_to_write:
        _write(w, field_type, field_key, value)
    return w


def _write(
    w: Writer, field_type: int, field_key: int, value: int | bytes | str | None
) -> None:
    from . import helpers

    if value is None:
        return

    # write_type
    if field_key <= 0xF:
        w.append((field_type << 4) | field_key)
    else:
        # this concerns two-bytes fields such as lastLedgerSequence
        w.append(field_type << 4)
        w.append(field_key)

    if field_type == _FIELD_TYPE_INT16:
        assert isinstance(value, int)
        w.extend(value.to_bytes(2, "big"))
    elif field_type == _FIELD_TYPE_INT32:
        assert isinstance(value, int)
        w.extend(value.to_bytes(4, "big"))
    elif field_type == _FIELD_TYPE_AMOUNT:
        assert isinstance(value, int)

        # serialize_amount
        if value < 0:
            raise ValueError("Only non-negative integers are supported")
        if value > helpers.MAX_ALLOWED_AMOUNT:
            raise ValueError("Value is too large")
        serialized_amount = bytearray(value.to_bytes(8, "big"))
        serialized_amount[0] &= 0x7F  # clear first bit to indicate XRP
        serialized_amount[0] |= 0x40  # set second bit to indicate positive number

        w.extend(serialized_amount)
    elif field_type == _FIELD_TYPE_ACCOUNT:
        assert isinstance(value, str)
        write_bytes_varint(w, helpers.decode_address(value))
    elif field_type == _FIELD_TYPE_VL:
        assert isinstance(value, (bytes, bytearray))
        write_bytes_varint(w, value)
    else:
        raise ValueError("Unknown field type")


def write_bytes_varint(w: Writer, value: bytes) -> None:
    """Serialize a variable length bytes."""
    append = w.append  # local_cache_attribute

    # write_varint
    # Implements variable-length int encoding from Ripple.
    # See: https://ripple.com/wiki/Binary_Format#Variable_Length_Data_Encoding
    val = len(value)
    if val < 0:
        raise ValueError("Only non-negative integers are supported")
    elif val < 192:
        append(val)
    elif val <= 12480:
        val -= 193
        append(193 + rshift(val, 8))
        append(val & 0xFF)
    elif val <= 918744:
        val -= 12481
        append(241 + rshift(val, 16))
        append(rshift(val, 8) & 0xFF)
        append(val & 0xFF)
    else:
        raise ValueError("Value is too large")

    w.extend(value)


def rshift(val: int, n: int) -> int:
    """
    Implements signed right-shift.
    See: http://stackoverflow.com/a/5833119/15677
    """
    return (val % 0x1_0000_0000) >> n
