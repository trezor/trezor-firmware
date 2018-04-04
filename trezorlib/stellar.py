import base64
import struct
import binascii
import xdrlib

def expand_path_or_default(client, address):
    """Uses client to parse address and returns an array of integers
    If no address is specified, the default of m/44'/148'/0' is used
    """
    if address:
        return client.expand_path(address)
    else:
        return client.expand_path("m/44'/148'/0'")


def address_from_public_key(pk_bytes):
    """Returns the base32-encoded version of pk_bytes (G...)
    """
    final_bytes = bytearray()

    # version
    final_bytes.append(6 << 3)
    # public key
    final_bytes.extend(pk_bytes)
    # checksum
    final_bytes.extend(struct.pack("<H", _crc16_checksum(final_bytes)))

    return base64.b32encode(final_bytes)

def address_to_public_key(address_str):
    """Returns the raw 32 bytes representing a public key by extracting
    it from the G... string
    """
    final_bytes = bytearray()
    decoded = base64.b32decode(address_str)

    # skip 0th byte (version) and last two bytes (checksum)
    return decoded[1:-2]


def parse_transaction_bytes(bytes):
    """Parses base64data into a StellarSignTx message
    """
    parsed = {}
    parsed["protocol_version"] = 1
    parsed["operations"] = []
    unpacker = xdrlib.Unpacker(bytes)

    parsed["source_account"] = _xdr_read_address(unpacker)
    parsed["fee"] = unpacker.unpack_uint()
    parsed["sequence_number"] = unpacker.unpack_uhyper()

    # Timebounds is an optional field
    parsed["timebounds_start"] = 0
    parsed["timebounds_end"] = 0
    has_timebounds = unpacker.unpack_bool()
    if has_timebounds:
        max_timebound = 2**32-1 # max unsigned 32-bit int (trezor does not support the full 64-bit time value)
        parsed["timebounds_start"] = unpacker.unpack_uhyper()
        parsed["timebounds_end"] = unpacker.unpack_uhyper()

        if parsed["timebounds_start"] > max_timebound or parsed["timebounds_start"] < 0:
            raise ValueError("Starting timebound out of range (must be between 0 and " + max_timebound)
        if parsed["timebounds_end"] > max_timebound or parsed["timebounds_end"] < 0:
            raise ValueError("Ending timebound out of range (must be between 0 and " + max_timebound)

    # memo type determines what optional fields are set
    parsed["memo_type"] = unpacker.unpack_uint()
    parsed["memo_text"] = None
    parsed["memo_id"] = None
    parsed["memo_hash"] = None

    # text
    if parsed["memo_type"] == 1:
        parsed["memo_text"] = unpacker.unpack_string()
    # id (64-bit uint)
    if parsed["memo_type"] == 2:
        parsed["memo_id"] = unpacker.unpack_uhyper()
    # hash / return are the same structure (32 bytes representing a hash)
    if parsed["memo_type"] == 3 or parsed["memo_type"] == 4:
        parsed["memo+hash"] = unpacker.unpack_fopaque(32)

    parsed["num_operations"] = unpacker.unpack_uint()

    for opIdx in range(0, parsed["num_operations"]):
        parsed["operations"].append(_parse_operation_bytes(unpacker))

    return parsed

def _parse_operation_bytes(unpacker):
    """Returns a dictionary describing the next operation as read from
    the byte stream in unpacker
    """
    op = {
        "source_account": None,
        "type": None
    }

    has_source_account = unpacker.unpack_bool()
    if has_source_account:
        op["source_account"] = unpacker.unpack_fopaque(32)

    op["type"] = unpacker.unpack_uint()

    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L16
    if op["type"] == 0:
        op["new_account"] = _xdr_read_address(unpacker)
        op["starting_balance"] = unpacker.unpack_hyper()

    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L54
    if op["type"] == 1:
        op["destination_account"] = _xdr_read_address(unpacker)
        op["asset"] = _xdr_read_asset(unpacker)
        op["amount"] = unpacker.unpack_hyper()

    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L72
    if op["type"] == 2:
        op["send_asset"] = _xdr_read_asset(unpacker)
        op["send_max"] = unpacker.unpack_hyper()
        op["destination_account"] = _xdr_read_address(unpacker)
        op["destination_asset"] = _xdr_read_asset(unpacker)
        op["destination_amount"] = unpacker.unpack_hyper()
        op["paths"] = []

        num_paths = unpacker.unpack_uint()
        for i in range(0, num_paths):
            op["paths"].append(_xdr_read_asset(unpacker))

    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L93
    if op["type"] == 3:
        op["selling_asset"] = _xdr_read_asset(unpacker)
        op["buying_asset"] = _xdr_read_asset(unpacker)
        op["amount"] = unpacker.unpack_hyper()
        op["price_n"] = unpacker.unpack_uint()
        op["price_d"] = unpacker.unpack_uint()
        op["offer_id"] = unpacker.unpack_uhyper()

    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L111
    if op["type"] == 4:
        op["selling_asset"] = _xdr_read_asset(unpacker)
        op["buying_asset"] = _xdr_read_asset(unpacker)
        op["amount"] = unpacker.unpack_hyper()
        op["price_n"] = unpacker.unpack_uint()
        op["price_d"] = unpacker.unpack_uint()

    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L129
    if op["type"] == 5:
        op["inflation_destination"] = None
        op["clear_flags"] = None
        op["set_flags"] = None
        op["master_weight"] = None
        op["low_threshold"] = None
        op["medium_threshold"] = None
        op["high_threshold"] = None
        op["home_domain"] = None
        op["signer_type"] = None
        op["signer_key"] = None
        op["signer_weight"] = None

        op["has_inflation_destination"] = unpacker.unpack_bool()
        if op["has_inflation_destination"]:
            op["inflation_destination"] = _xdr_read_address(unpacker)

        op["has_clear_flags"] = unpacker.unpack_bool()
        if op["has_clear_flags"]:
            op["clear_flags"] = unpacker.unpack_uint()

        op["has_set_flags"] = unpacker.unpack_bool()
        if op["has_set_flags"]:
            op["set_flags"] = unpacker.unpack_uint()

        op["has_master_weight"] = unpacker.unpack_bool()
        if op["has_master_weight"]:
            op["master_weight"] = unpacker.unpack_uint()

        op["has_low_threshold"] = unpacker.unpack_bool()
        if op["has_low_threshold"]:
            op["low_threshold"] = unpacker.unpack_uint()

        op["has_medium_threshold"] = unpacker.unpack_bool()
        if op["has_medium_threshold"]:
            op["medium_threshold"] = unpacker.unpack_uint()

        op["has_high_threshold"] = unpacker.unpack_bool()
        if op["has_high_threshold"]:
            op["high_threshold"] = unpacker.unpack_uint()

        op["has_home_domain"] = unpacker.unpack_bool()
        if op["has_home_domain"]:
            op["home_domain"] = unpacker.unpack_string()

        op["has_signer"] = unpacker.unpack_bool()
        if op["has_signer"]:
            op["signer_type"] = unpacker.unpack_uint()
            op["signer_key"] = unpacker.unpack_fopaque(32)
            op["signer_weight"] = unpacker.unpack_uint()

    # Change Trust
    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L156
    if op["type"] == 6:
        op["asset"] = _xdr_read_asset(unpacker)
        op["limit"] = unpacker.unpack_uhyper()

    # Allow Trust
    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L173
    if op["type"] == 7:
        op["trusted_account"] = _xdr_read_address(unpacker)
        op["asset_type"] = unpacker.unpack_uint()

        if op["asset_type"] == 1:
            op["asset_code"] = unpacker.unpack_fstring(4)
        if op["asset_type"] == 2:
            op["asset_code"] = unpacker.unpack_fstring(12)

        op["is_authorized"] = unpacker.unpack_bool()

    # Merge Account
    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L251
    if op["type"] == 8:
        op["destination_account"] = _xdr_read_address(unpacker)

    # Inflation is not implemented since any account can send this operation

    # Manage Data
    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L218
    if op["type"] == 10:
        op["key"] = unpacker.unpack_string()

        op["value"] = None
        op["has_value"] = unpacker.unpack_bool()
        if op["has_value"]:
            op["value"] = unpacker.unpack_opaque()

    # Bump Sequence
    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L269
    if op["type"] == 11:
        op["bump_to"] = unpacker.unpack_uhyper()

    return op

def _xdr_read_asset(unpacker):
    """Reads a stellar Asset from unpacker"""
    asset = {
        "type": unpacker.unpack_uint(),
        "code": None,
        "issuer": None
    }

    # alphanum 4
    if asset["type"] == 1:
        asset["code"] = unpacker.unpack_fstring(4)
        asset["issuer"] = _xdr_read_address(unpacker)

    if asset["type"] == 2:
        asset["code"] = unpacker.unpack_fstring(12)
        asset["issuer"] = _xdr_read_address(unpacker)

    return asset


def _xdr_read_address(unpacker):
    """Reads a stellar address and returns the 32-byte
    data representing the address
    """
    # First 4 bytes are the address type
    address_type = unpacker.unpack_uint()
    if address_type != 0:
        raise ValueError("Unsupported address type")

    return unpacker.unpack_fopaque(32)

def _crc16_checksum(bytes):
    """Returns the CRC-16 checksum of bytearray bytes

    Ported from Java implementation at: http://introcs.cs.princeton.edu/java/61data/CRC16CCITT.java.html

    Initial value changed to 0x0000 to match Stellar configuration.
    """
    crc = 0x0000
    polynomial = 0x1021

    for byte in bytes:
        for i in range(0, 8):
            bit = ((byte >> (7 - i) & 1) == 1)
            c15 = ((crc >> 15 & 1) == 1)
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial

    return crc & 0xffff