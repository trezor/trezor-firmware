# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import base64
import struct
import xdrlib

from . import messages
from .tools import CallException, expect

# Memo types
MEMO_TYPE_NONE = 0
MEMO_TYPE_TEXT = 1
MEMO_TYPE_ID = 2
MEMO_TYPE_HASH = 3
MEMO_TYPE_RETURN = 4

# Asset types
ASSET_TYPE_NATIVE = 0
ASSET_TYPE_ALPHA4 = 1
ASSET_TYPE_ALPHA12 = 2

# Operations
OP_CREATE_ACCOUNT = 0
OP_PAYMENT = 1
OP_PATH_PAYMENT = 2
OP_MANAGE_OFFER = 3
OP_CREATE_PASSIVE_OFFER = 4
OP_SET_OPTIONS = 5
OP_CHANGE_TRUST = 6
OP_ALLOW_TRUST = 7
OP_ACCOUNT_MERGE = 8
OP_INFLATION = 9  # Included for documentation purposes, not supported by Trezor
OP_MANAGE_DATA = 10
OP_BUMP_SEQUENCE = 11


DEFAULT_BIP32_PATH = "m/44h/148h/0h"
# Stellar's BIP32 differs to Bitcoin's see https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md
DEFAULT_NETWORK_PASSPHRASE = "Public Global Stellar Network ; September 2015"


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

    return base64.b32encode(final_bytes).decode()


def address_to_public_key(address_str):
    """Returns the raw 32 bytes representing a public key by extracting
    it from the G... string
    """
    decoded = base64.b32decode(address_str)

    # skip 0th byte (version) and last two bytes (checksum)
    return decoded[1:-2]


def parse_transaction_bytes(tx_bytes):
    """Parses base64data into a map with the following keys:
        tx - a StellarSignTx describing the transaction header
        operations - an array of protobuf message objects for each operation
    """
    tx = messages.StellarSignTx()
    unpacker = xdrlib.Unpacker(tx_bytes)

    tx.source_account = _xdr_read_address(unpacker)
    tx.fee = unpacker.unpack_uint()
    tx.sequence_number = unpacker.unpack_uhyper()

    # Timebounds is an optional field
    if unpacker.unpack_bool():
        max_timebound = 2 ** 32 - 1  # max unsigned 32-bit int
        # (trezor does not support the full 64-bit time value)

        tx.timebounds_start = unpacker.unpack_uhyper()
        tx.timebounds_end = unpacker.unpack_uhyper()

        if tx.timebounds_start > max_timebound or tx.timebounds_start < 0:
            raise ValueError(
                "Starting timebound out of range (must be between 0 and "
                + max_timebound
            )
        if tx.timebounds_end > max_timebound or tx.timebounds_end < 0:
            raise ValueError(
                "Ending timebound out of range (must be between 0 and " + max_timebound
            )

    # memo type determines what optional fields are set
    tx.memo_type = unpacker.unpack_uint()

    # text
    if tx.memo_type == MEMO_TYPE_TEXT:
        tx.memo_text = unpacker.unpack_string()
    # id (64-bit uint)
    if tx.memo_type == MEMO_TYPE_ID:
        tx.memo_id = unpacker.unpack_uhyper()
    # hash / return are the same structure (32 bytes representing a hash)
    if tx.memo_type == MEMO_TYPE_HASH or tx.memo_type == MEMO_TYPE_RETURN:
        tx.memo_hash = unpacker.unpack_fopaque(32)

    tx.num_operations = unpacker.unpack_uint()

    operations = []
    for _ in range(tx.num_operations):
        operations.append(_parse_operation_bytes(unpacker))

    return tx, operations


def _parse_operation_bytes(unpacker):
    """Returns a protobuf message representing the next operation as read from
    the byte stream in unpacker
    """

    # Check for and parse optional source account field
    source_account = None
    if unpacker.unpack_bool():
        source_account = unpacker.unpack_fopaque(32)

    # Operation type (See OP_ constants)
    type = unpacker.unpack_uint()

    if type == OP_CREATE_ACCOUNT:
        return messages.StellarCreateAccountOp(
            source_account=source_account,
            new_account=_xdr_read_address(unpacker),
            starting_balance=unpacker.unpack_hyper(),
        )

    if type == OP_PAYMENT:
        return messages.StellarPaymentOp(
            source_account=source_account,
            destination_account=_xdr_read_address(unpacker),
            asset=_xdr_read_asset(unpacker),
            amount=unpacker.unpack_hyper(),
        )

    if type == OP_PATH_PAYMENT:
        op = messages.StellarPathPaymentOp(
            source_account=source_account,
            send_asset=_xdr_read_asset(unpacker),
            send_max=unpacker.unpack_hyper(),
            destination_account=_xdr_read_address(unpacker),
            destination_asset=_xdr_read_asset(unpacker),
            destination_amount=unpacker.unpack_hyper(),
            paths=[],
        )

        num_paths = unpacker.unpack_uint()
        for _ in range(num_paths):
            op.paths.append(_xdr_read_asset(unpacker))

        return op

    if type == OP_MANAGE_OFFER:
        return messages.StellarManageOfferOp(
            source_account=source_account,
            selling_asset=_xdr_read_asset(unpacker),
            buying_asset=_xdr_read_asset(unpacker),
            amount=unpacker.unpack_hyper(),
            price_n=unpacker.unpack_uint(),
            price_d=unpacker.unpack_uint(),
            offer_id=unpacker.unpack_uhyper(),
        )

    if type == OP_CREATE_PASSIVE_OFFER:
        return messages.StellarCreatePassiveOfferOp(
            source_account=source_account,
            selling_asset=_xdr_read_asset(unpacker),
            buying_asset=_xdr_read_asset(unpacker),
            amount=unpacker.unpack_hyper(),
            price_n=unpacker.unpack_uint(),
            price_d=unpacker.unpack_uint(),
        )

    if type == OP_SET_OPTIONS:
        op = messages.StellarSetOptionsOp(source_account=source_account)

        # Inflation destination
        if unpacker.unpack_bool():
            op.inflation_destination_account = _xdr_read_address(unpacker)

        # clear flags
        if unpacker.unpack_bool():
            op.clear_flags = unpacker.unpack_uint()

        # set flags
        if unpacker.unpack_bool():
            op.set_flags = unpacker.unpack_uint()

        # master weight
        if unpacker.unpack_bool():
            op.master_weight = unpacker.unpack_uint()

        # low threshold
        if unpacker.unpack_bool():
            op.low_threshold = unpacker.unpack_uint()

        # medium threshold
        if unpacker.unpack_bool():
            op.medium_threshold = unpacker.unpack_uint()

        # high threshold
        if unpacker.unpack_bool():
            op.high_threshold = unpacker.unpack_uint()

        # home domain
        if unpacker.unpack_bool():
            op.home_domain = unpacker.unpack_string()

        # signer
        if unpacker.unpack_bool():
            op.signer_type = unpacker.unpack_uint()
            op.signer_key = unpacker.unpack_fopaque(32)
            op.signer_weight = unpacker.unpack_uint()

        return op

    if type == OP_CHANGE_TRUST:
        return messages.StellarChangeTrustOp(
            source_account=source_account,
            asset=_xdr_read_asset(unpacker),
            limit=unpacker.unpack_uhyper(),
        )

    if type == OP_ALLOW_TRUST:
        op = messages.StellarAllowTrustOp(
            source_account=source_account,
            trusted_account=_xdr_read_address(unpacker),
            asset_type=unpacker.unpack_uint(),
        )

        if op.asset_type == ASSET_TYPE_ALPHA4:
            op.asset_code = unpacker.unpack_fstring(4)
        if op.asset_type == ASSET_TYPE_ALPHA12:
            op.asset_code = unpacker.unpack_fstring(12)

        op.is_authorized = unpacker.unpack_bool()

        return op

    if type == OP_ACCOUNT_MERGE:
        return messages.StellarAccountMergeOp(
            source_account=source_account,
            destination_account=_xdr_read_address(unpacker),
        )

    # Inflation is not implemented since anyone can submit this operation to the network

    if type == OP_MANAGE_DATA:
        op = messages.StellarManageDataOp(
            source_account=source_account, key=unpacker.unpack_string()
        )

        # Only set value if the field is present
        if unpacker.unpack_bool():
            op.value = unpacker.unpack_opaque()

        return op

    # Bump Sequence
    # see: https://github.com/stellar/stellar-core/blob/master/src/xdr/Stellar-transaction.x#L269
    if type == OP_BUMP_SEQUENCE:
        return messages.StellarBumpSequenceOp(
            source_account=source_account, bump_to=unpacker.unpack_uhyper()
        )

    raise ValueError("Unknown operation type: " + str(type))


def _xdr_read_asset(unpacker):
    """Reads a stellar Asset from unpacker"""
    asset = messages.StellarAssetType(type=unpacker.unpack_uint())

    if asset.type == ASSET_TYPE_ALPHA4:
        asset.code = unpacker.unpack_fstring(4)
        asset.issuer = _xdr_read_address(unpacker)

    if asset.type == ASSET_TYPE_ALPHA12:
        asset.code = unpacker.unpack_fstring(12)
        asset.issuer = _xdr_read_address(unpacker)

    return asset


def _xdr_read_address(unpacker):
    """Reads a stellar address and returns the string representing the address
    This method assumes the encoded address is a public address (starting with G)
    """
    # First 4 bytes are the address type
    address_type = unpacker.unpack_uint()
    if address_type != 0:
        raise ValueError("Unsupported address type")

    return address_from_public_key(unpacker.unpack_fopaque(32))


def _crc16_checksum(bytes):
    """Returns the CRC-16 checksum of bytearray bytes

    Ported from Java implementation at: http://introcs.cs.princeton.edu/java/61data/CRC16CCITT.java.html

    Initial value changed to 0x0000 to match Stellar configuration.
    """
    crc = 0x0000
    polynomial = 0x1021

    for byte in bytes:
        for i in range(8):
            bit = (byte >> (7 - i) & 1) == 1
            c15 = (crc >> 15 & 1) == 1
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial

    return crc & 0xFFFF


# ====== Client functions ====== #


@expect(messages.StellarAddress, field="address")
def get_address(client, address_n, show_display=False):
    return client.call(
        messages.StellarGetAddress(address_n=address_n, show_display=show_display)
    )


def sign_tx(
    client, tx, operations, address_n, network_passphrase=DEFAULT_NETWORK_PASSPHRASE
):
    tx.network_passphrase = network_passphrase
    tx.address_n = address_n
    tx.num_operations = len(operations)
    # Signing loop works as follows:
    #
    # 1. Start with tx (header information for the transaction) and operations (an array of operation protobuf messagess)
    # 2. Send the tx header to the device
    # 3. Receive a StellarTxOpRequest message
    # 4. Send operations one by one until all operations have been sent. If there are more operations to sign, the device will send a StellarTxOpRequest message
    # 5. The final message received will be StellarSignedTx which is returned from this method
    resp = client.call(tx)
    try:
        while isinstance(resp, messages.StellarTxOpRequest):
            resp = client.call(operations.pop(0))
    except IndexError:
        # pop from empty list
        raise CallException(
            "Stellar.UnexpectedEndOfOperations",
            "Reached end of operations without a signature.",
        ) from None

    if not isinstance(resp, messages.StellarSignedTx):
        raise CallException(messages.FailureType.UnexpectedMessage, resp)

    if operations:
        raise CallException(
            "Stellar.UnprocessedOperations",
            "Received a signature before processing all operations.",
        )

    return resp
