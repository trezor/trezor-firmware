# Serializes into the Ripple Format
#
# Based on https://github.com/ripple/xrpl-dev-portal/tree/master/content/_code-samples/tx-serialization
# Docs at https://xrpl.org/serialization.html and https://xrpl.org/transaction-common-fields.html

import ubinascii

import protobuf
from trezor.messages.RippleIssuedAmount import RippleIssuedAmount
from trezor.messages.RippleSignTx import RippleSignTx
from trezor.wire import DataError

from . import helpers

from apps.ripple.definitions import TRANSACTIONS
from apps.ripple.helpers import bytes_to_hex


class IssuedAmount:
    MIN_MANTISSA = 10 ** 15
    MAX_MANTISSA = 10 ** 16 - 1
    MIN_EXP = -96
    MAX_EXP = 80

    def __init__(self, strnum):
        self.strnum = strnum

    def to_bytes(self):
        if self.strnum.lower().count("e") == 1:
            # Scientific notation
            parts = self.strnum.lower().split("e")
            if len(parts) != 2:
                # Can't be a valid number in scientific notation
                raise DataError("Could not parse amount value")
            digits, exp, sign = self.parse_number(parts[0])
            try:
                # Add exponent
                exp += int(parts[1])
            except ValueError:
                raise DataError("Could not parse amount value")
        else:
            digits, exp, sign = self.parse_number(self.strnum)

        if all(i == 0 for i in digits):
            # Special case for zero
            return self.canonical_zero_serial()

        # Convert components to integers ---------------------------------------
        mantissa = int("".join([str(d) for d in digits]))

        # Canonicalize to expected range ---------------------------------------
        while mantissa < self.MIN_MANTISSA and exp > self.MIN_EXP:
            mantissa *= 10
            exp -= 1

        while mantissa > self.MAX_MANTISSA:
            if exp >= self.MAX_EXP:
                raise DataError("amount overflow")
            mantissa //= 10
            exp += 1

        if exp < self.MIN_EXP or mantissa < self.MIN_MANTISSA:
            # Round to zero
            return self.canonical_zero_serial()

        if exp > self.MAX_EXP or mantissa > self.MAX_MANTISSA:
            raise DataError("amount overflow")

        # Convert to bytes -----------------------------------------------------
        serial = 0x8000000000000000  # "Not XRP" bit set
        if sign == 0:
            serial |= 0x4000000000000000  # "Is positive" bit set
        serial |= (exp + 97) << 54  # next 8 bits are exponent
        serial |= mantissa  # last 54 bits are mantissa

        return serial.to_bytes(8, "big")

    @staticmethod
    def canonical_zero_serial():
        """
        Returns canonical format for zero (a special case):
        - "Not XRP" bit = 1
        - Everything else is zeroes
        - Arguably this means it's canonically written as "negative zero"
          because the encoding usually uses 1 for positive.
        """
        return (0x8000000000000000).to_bytes(8, "big")

    def parse_number(self, number: str) -> (int, int, []):
        """
        :param number: A string representing a number in scientific or standard notation
        :return: The number represented by a list of digits, a sign bit (0 for positive, 1 for negative) and a exponent
        """
        if number.count(".") == 1:
            # Decimal
            sign, exp, digits = self.parse_decimal(number)
        elif number.count(".") == 0:
            # Integer
            sign, exp, digits = self.parse_int(number)
        else:
            raise DataError("Could not parse amount value")
        return digits, exp, sign

    @staticmethod
    def parse_decimal(number: str) -> (int, int, list):
        try:
            number = number.strip()
            sign = 1 if int(number.split(".")[0]) < 0 else 0
            exp = (number.find(".") + 1) - len(number)
            digits = [int(d) for d in str(abs(int("".join(number.split(".")))))]
            return sign, exp, digits
        except ValueError:
            raise DataError("Could not parse amount value")

    @staticmethod
    def parse_int(number: str) -> (int, int, list):
        try:
            sign = 1 if int(number) < 0 else 0
            exp = 0
            digits = [int(d) for d in str(abs(int(number)))]
            return sign, exp, digits
        except ValueError:
            raise DataError("Could not parse amount value")


def field_sort_key(field):
    """Return a tuple sort key for a given field name"""
    field_name = field[0]
    field_type_name = TRANSACTIONS["FIELDS"][field_name]["type"]
    return (
        TRANSACTIONS["TYPES"][field_type_name],
        TRANSACTIONS["FIELDS"][field_name]["nth"],
    )


def field_id(field_name):
    """
    Returns the unique field ID for a given field name.
    This field ID consists of the type code and field code, in 1 to 3 bytes
    depending on whether those values are "common" (<16) or "uncommon" (>=16)
    """
    field_type_name = TRANSACTIONS["FIELDS"][field_name]["type"]
    type_code = TRANSACTIONS["TYPES"][field_type_name]
    field_code = TRANSACTIONS["FIELDS"][field_name]["nth"]

    # Codes must be nonzero and fit in 1 byte
    if field_code <= 0 or field_code > 255:
        raise ValueError("Field code not nonzero or >255")
    if type_code <= 0 or type_code > 255:
        raise ValueError("Type code not nonzero or >255")

    if type_code < 16 and field_code < 16:
        # high 4 bits is the type_code
        # low 4 bits is the field code
        combined_code = (type_code << 4) | field_code
        return uint8_to_bytes(combined_code)
    elif type_code >= 16 > field_code:
        # first 4 bits are zeroes
        # next 4 bits is field code
        # next byte is type code
        byte1 = uint8_to_bytes(field_code)
        byte2 = uint8_to_bytes(type_code)
        return b"".join((byte1, byte2))
    elif type_code < 16 <= field_code:
        # first 4 bits is type code
        # next 4 bits are zeroes
        # next byte is field code
        byte1 = uint8_to_bytes(type_code << 4)
        byte2 = uint8_to_bytes(field_code)
        return b"".join((byte1, byte2))
    else:  # both are >= 16
        # first byte is all zeroes
        # second byte is type
        # third byte is field code
        byte2 = uint8_to_bytes(type_code)
        byte3 = uint8_to_bytes(field_code)
        return b"".join((bytes(1), byte2, byte3))


def vl_encode(vl_contents):
    """
    Helper function for length-prefixed fields including Blob types
    and some AccountID types.

    Encodes arbitrary binary data with a length prefix. The length of the prefix
    is 1-3 bytes depending on the length of the contents:

    Content length <= 192 bytes: prefix is 1 byte
    192 bytes < Content length <= 12480 bytes: prefix is 2 bytes
    12480 bytes < Content length <= 918744 bytes: prefix is 3 bytes
    """

    vl_len = len(vl_contents)
    if vl_len <= 192:
        len_byte = vl_len.to_bytes(1, "big")
        return b"".join((len_byte, vl_contents))
    elif vl_len <= 12480:
        vl_len -= 193
        byte1 = ((vl_len >> 8) + 193).to_bytes(1, "big")
        byte2 = (vl_len & 0xFF).to_bytes(1, "big")
        return b"".join((byte1, byte2, vl_contents))
    elif vl_len <= 918744:
        vl_len -= 12481
        byte1 = (241 + (vl_len >> 16)).to_bytes(1, "big")
        byte2 = ((vl_len >> 8) & 0xFF).to_bytes(1, "big")
        byte3 = (vl_len & 0xFF).to_bytes(1, "big")
        return b"".join((byte1, byte2, byte3, vl_contents))

    raise ValueError("VariableLength field must be <= 918744 bytes long")


# Individual field type serialization routines ---------------------------------


def accountid_to_bytes(address):
    """
    Serialize an AccountID field type. These are length-prefixed.

    Some fields contain nested non-length-prefixed AccountIDs directly; those
    call helpers.decode_address() instead of this function.
    """
    return vl_encode(helpers.decode_address(address))


def amount_to_bytes(a):
    """
    Serializes an "Amount" type, which can be either XRP or an issued currency:
    - XRP: 64 bits; 0, followed by 1 ("is positive"), followed by 62 bit UInt amount
    - Issued Currency: 64 bits of amount, followed by 160 bit currency code and
      160 bit issuer AccountID.
    """
    if type(a) == int:
        xrp_amt = a
        if xrp_amt >= 0:
            if xrp_amt > 10 ** 17:
                raise ValueError("Value is too large")
            # set the "is positive" bit -- this is backwards from usual two's complement!
            xrp_amt = xrp_amt | 0x4000000000000000
        else:
            if xrp_amt < -(10 ** 17):
                raise ValueError("Value is too small")
            # convert to absolute value, leaving the "is positive" bit unset
            xrp_amt = -xrp_amt
        return xrp_amt.to_bytes(8, "big")
    elif type(a) is RippleIssuedAmount:
        issued_amt = IssuedAmount(a.value).to_bytes()
        currency_code = currency_code_to_bytes(a.currency)
        return issued_amt + currency_code + helpers.decode_address(a.issuer)
    else:
        raise ValueError("amount must be XRP string or RippleIssuedAmount")


def array_to_bytes(array):
    """
    Serialize an array of objects from decoded JSON.
    Each member object must have a type wrapper and an inner object.
    For example:
    [
        {
            // wrapper object
            "Memo": {
                // inner object
                "MemoType": "687474703a2f2f6578616d706c652e636f6d2f6d656d6f2f67656e65726963",
                "MemoData": "72656e74"
            }
        }
    ]
    """
    members_as_bytes = []
    for el in array:
        wrapper_key = el.get_fields()[1][0]
        members_as_bytes.append(field_to_bytes(field_name=wrapper_key, field_val=el))
    members_as_bytes.append(field_id("array_end_marker"))
    return b"".join(members_as_bytes)


def blob_to_bytes(field_val):
    """
    Serializes a string of hex as binary data with a length prefix.
    """
    vl_contents = ubinascii.unhexlify(field_val)
    return vl_encode(vl_contents)


def currency_code_to_bytes(code_string, xrp_ok=False):
    if len(code_string) == 3 and code_string.isalpha():
        # ISO 4217-like code
        if code_string == "XRP":
            if xrp_ok:
                # Rare, but when the currency code "XRP" is serialized, it's
                # a special-case all zeroes.
                return bytes(20)
            raise ValueError("issued currency can't be XRP")

        code_ascii = code_string.encode("ASCII")
        # standard currency codes: https://xrpl.org/currency-formats.html#standard-currency-codes
        # 8 bits type code (0x00)
        # 88 bits reserved (0's)
        # 24 bits ASCII
        # 16 bits version (0x00)
        # 24 bits reserved (0's)
        return b"".join((bytes(12), code_ascii, bytes(5)))
    else:
        # raw hex code
        return ubinascii.unhexlify(code_string)  # requires Python 3.5+


def hash128_to_bytes(contents):
    """
    Serializes a hexadecimal string as binary and confirms that it's 128 bits
    """
    b = hash_to_bytes(contents)
    if len(b) != 16:  # 16 bytes = 128 bits
        raise ValueError("Hash128 is not 128 bits long")
    return b


def hash256_to_bytes(contents):
    b = hash_to_bytes(contents)
    if len(b) != 32:  # 32 bytes = 256 bits
        raise ValueError("Hash256 is not 256 bits long")
    return b


def hash_to_bytes(contents):
    """
    Helper function; serializes a hash value from a hexadecimal string
    of any length.
    """
    return ubinascii.unhexlify(contents)


def object_to_bytes(obj):
    """
    Serialize an object from decoded JSON.
    Each object must have a type wrapper and an inner object. For example:

    {
        // type wrapper
        "SignerEntry": {
            // inner object
            "Account": "rUpy3eEg8rqjqfUoLeBnZkscbKbFsKXC3v",
            "SignerWeight": 1
        }
    }

    Puts the child fields (e.g. Account, SignerWeight) in canonical order
    and appends an object end marker.
    """
    wrapper_key = obj.get_fields()[1][0]
    inner_obj = getattr(obj, wrapper_key)
    keys = get_fields(inner_obj)
    child_order = sorted(keys, key=field_sort_key)
    fields_as_bytes = []
    for field_name, path in child_order:
        field_val = getattr(inner_obj, field_name)
        field_bytes = field_to_bytes(field_name, field_val)
        fields_as_bytes.append(field_bytes)

    fields_as_bytes.append(field_id("object_end_marker"))
    return b"".join(fields_as_bytes)


def pathset_to_bytes(pathset):
    """
    Serialize a PathSet, which is an array of arrays,
    where each inner array represents one possible payment path.
    A path consists of "path step" objects in sequence, each with one or
    more of "account", "currency", and "issuer" fields, plus (ignored) "type"
    and "type_hex" fields which indicate which fields are present.
    (We re-create the type field for serialization based on which of the core
    3 fields are present.)
    """

    if not len(pathset):
        raise ValueError("PathSet type must not be empty")

    paths_as_bytes = []
    for n in range(len(pathset)):
        path = path_as_bytes(pathset[n])
        paths_as_bytes.append(path)
        if n + 1 == len(pathset):  # last path; add an end byte
            paths_as_bytes.append(ubinascii.unhexlify("00"))
        else:  # add a path separator byte
            paths_as_bytes.append(ubinascii.unhexlify("ff"))

    return b"".join(paths_as_bytes)


def path_as_bytes(path):
    """
    Helper function for representing one member of a pathset as a bytes object
    """
    path = path.path

    if not len(path):
        raise ValueError("Path must not be empty")

    path_contents = []
    for step in path:
        step_data = []
        type_byte = 0
        if step.account is not None:
            type_byte |= 0x01
            step_data.append(helpers.decode_address(step.account))
        if step.currency is not None:
            type_byte |= 0x10
            step_data.append(currency_code_to_bytes(step.currency, xrp_ok=True))
        if step.issuer is not None:
            type_byte |= 0x20
            step_data.append(helpers.decode_address(step.issuer))
        step_data = [uint8_to_bytes(type_byte)] + step_data
        path_contents += step_data

    return b"".join(path_contents)


def tx_type_to_bytes(txtype):
    """
    TransactionType field is a special case that is written in the input
    as a string name but in binary as a UInt16.
    """
    type_uint = TRANSACTIONS["TRANSACTION_TYPES"][txtype]
    return uint16_to_bytes(type_uint)


def uint8_to_bytes(i):
    return i.to_bytes(1, "big")


def uint16_to_bytes(i):
    return i.to_bytes(2, "big")


def uint32_to_bytes(i):
    return i.to_bytes(4, "big")


# Core serialization logic -----------------------------------------------------


def field_to_bytes(field_name, field_val):
    """
    Returns a bytes object containing the serialized version of a field
    including its field ID prefix.
    """
    field_type = TRANSACTIONS["FIELDS"][field_name]["type"]

    id_prefix = field_id(field_name)

    if field_name == "transaction_type":
        # Special case: convert from string to UInt16
        return b"".join((id_prefix, tx_type_to_bytes(field_val)))

    dispatch = {
        # TypeName: function(field): bytes object
        "AccountID": accountid_to_bytes,
        "Amount": amount_to_bytes,
        "Blob": blob_to_bytes,
        "Hash128": hash128_to_bytes,
        "Hash256": hash256_to_bytes,
        "PathSet": pathset_to_bytes,
        "STArray": array_to_bytes,
        "STObject": object_to_bytes,
        "UInt8": uint8_to_bytes,
        "UInt16": uint16_to_bytes,
        "UInt32": uint32_to_bytes,
    }
    field_binary = dispatch[field_type](field_val)
    return b"".join((id_prefix, field_binary))


def get_fields(tx: RippleSignTx, transaction_type: str = None):
    """
    Generate a list of all keys and their path in a transaction
    :param tx: A RippleSignTx object containing a transaction
    :param transaction_type: The transaction type
    :return: A list of tuples containing (field_name, ["list","with","path"])
    """
    keys = []
    for field in tx.get_fields().values():
        if getattr(tx, field[0]) is not None and getattr(tx, field[0]) != []:
            if transaction_type is not None and field[0] == transaction_type:
                # For the transaction specific keys we need to read subfields due to protobuf structure
                for sub_field in getattr(tx, field[0]).get_fields().values():
                    if (
                        getattr(getattr(tx, field[0]), sub_field[0]) is not None
                        and getattr(getattr(tx, field[0]), sub_field[0]) != []
                    ):
                        keys.append((sub_field[0], [field[0], sub_field[0]]))
            elif field[0].startswith("issued_"):
                # Separation between issued and non-issued currencies is only needed due to protobuf
                # structure
                keys.append((field[0].replace("issued_", ""), [field[0]]))
            else:
                keys.append((field[0], [field[0]]))
    return keys


def get_field(proto_message: protobuf.MessageType, path: []):
    """
    Get field from message object
    :param proto_message: Object to get field from
    :param path: Where to find the field, represented as a list of attribute names
    :return: field value
    """
    p = path[0]
    path = path[1:]
    field = getattr(proto_message, p)
    if len(path) == 0:
        return field
    else:
        return get_field(field, path)


def serialize(tx: RippleSignTx, transaction_type, for_signing=False, signature=None):
    """
    Takes a transaction message and returns a bytes object representing
    the transaction in binary format.

    If for_signing=True, then only signing fields are serialized, so the
    output can be used to sign the transaction.
    """
    fields = get_fields(tx, transaction_type)
    # address_n and multisign are not part of the serialized message
    if ("address_n", ["address_n"]) in fields:
        fields.remove(("address_n", ["address_n"]))

    # Multisign transactions should not contain TxnSignature amongst the common fields
    if signature and tx.signing_pub_key != "":
        fields.append(("txn_signature", []))
        signature = bytes_to_hex(signature)

    field_order = sorted(fields, key=field_sort_key)

    fields_as_bytes = []
    for field_name, path in field_order:
        if for_signing and not TRANSACTIONS["FIELDS"][field_name]["isSigningField"]:
            # Skip non-signing fields in for_signing mode.
            continue
        elif field_name == "txn_signature":
            field_val = signature
        elif field_name == "transaction_type":
            field_val = transaction_type
        else:
            field_val = get_field(tx, path)
        field_bytes = field_to_bytes(field_name, field_val)

        fields_as_bytes.append(field_bytes)

    all_serial = b"".join(fields_as_bytes)
    return all_serial
