# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import pytest

from trezorlib import tools
from trezorlib.debuglink import DebugSession as Session

from . import testapp_ext
from .common import parametrize_using_common_fixtures
from .testapp_ext import INVALID_ENCODING, SdkError, raises

# The SDK's base58 functions handle at most this much (decoded) data.
MAX_DATA = 128

INVALID_STRINGS = [
    pytest.param("0", id="zero"),
    pytest.param("O", id="capital_o"),
    pytest.param("I", id="capital_i"),
    pytest.param("l", id="small_l"),
    pytest.param("2+3", id="plus"),
    pytest.param("2 3", id="space"),
    pytest.param("23\n", id="newline"),
    pytest.param("2č", id="non_ascii"),
    pytest.param("1\x001", id="inner_nul"),
]


# ============================================================================
# Base58
# ============================================================================


@parametrize_using_common_fixtures("base58.json")
def test_base58_encode(session: Session, instance_id: int, parameters, result):
    data = bytes.fromhex(parameters["data"])
    assert testapp_ext.base58_encode(session, instance_id, data) == result["encoded"]


@parametrize_using_common_fixtures("base58.json")
def test_base58_decode(session: Session, instance_id: int, parameters, result):
    data = testapp_ext.base58_decode(session, instance_id, result["encoded"])
    assert data.hex() == parameters["data"]


def test_base58_encode_too_long(session: Session, instance_id: int):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58_encode(session, instance_id, b"\x01" * (MAX_DATA + 1))


@pytest.mark.parametrize("encoded", INVALID_STRINGS)
def test_base58_decode_invalid(session: Session, instance_id: int, encoded: str):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58_decode(session, instance_id, encoded)


@pytest.mark.parametrize(
    "encoded",
    [
        # One more leading '1' (zero byte) than fits.
        pytest.param("1" * (MAX_DATA + 1), id="zeros"),
        # A number one byte longer than fits.
        pytest.param(tools.b58encode(b"\x01" * (MAX_DATA + 1)), id="number"),
        # Longer than any encoding of at most MAX_DATA bytes.
        pytest.param("2" * 300, id="string"),
    ],
)
def test_base58_decode_too_long(session: Session, instance_id: int, encoded: str):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58_decode(session, instance_id, encoded)


# ============================================================================
# Base58Check
# ============================================================================


@parametrize_using_common_fixtures("base58check.json")
def test_base58check_encode(session: Session, instance_id: int, parameters, result):
    data = bytes.fromhex(parameters["data"])
    assert (
        testapp_ext.base58check_encode(session, instance_id, data) == result["encoded"]
    )


@parametrize_using_common_fixtures("base58check.json")
def test_base58check_decode(session: Session, instance_id: int, parameters, result):
    data = testapp_ext.base58check_decode(session, instance_id, result["encoded"])
    assert data.hex() == parameters["data"]


def test_base58check_encode_too_long(session: Session, instance_id: int):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58check_encode(session, instance_id, b"\x01" * (MAX_DATA + 1))


@pytest.mark.parametrize("encoded", INVALID_STRINGS)
def test_base58check_decode_invalid(session: Session, instance_id: int, encoded: str):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58check_decode(session, instance_id, encoded)


def test_base58check_decode_too_long(session: Session, instance_id: int):
    encoded = tools.b58check_encode(b"\x01" * (MAX_DATA + 1))
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58check_decode(session, instance_id, encoded)


@pytest.mark.parametrize(
    "encoded",
    [
        pytest.param("", id="empty"),
        # Fewer than the 4 checksum bytes.
        pytest.param(tools.b58encode(b"\x01\x02\x03"), id="shorter_than_checksum"),
        # Valid base58, but not followed by its checksum.
        pytest.param(tools.b58encode(b"hello world"), id="no_checksum"),
    ],
)
def test_base58check_decode_malformed(session: Session, instance_id: int, encoded: str):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58check_decode(session, instance_id, encoded)


def test_base58check_decode_bad_checksum(session: Session, instance_id: int):
    """Every single corrupted checksum byte is caught."""
    raw = b"payload" + tools.btc_hash(b"payload")[:4]
    for i in range(len(b"payload"), len(raw)):
        corrupted = bytearray(raw)
        corrupted[i] ^= 0x01
        with raises(SdkError.DataError, INVALID_ENCODING):
            testapp_ext.base58check_decode(
                session, instance_id, tools.b58encode(bytes(corrupted))
            )


def test_base58check_decode_bad_payload(session: Session, instance_id: int):
    """A corrupted payload byte no longer matches the checksum."""
    raw = bytearray(b"payload" + tools.btc_hash(b"payload")[:4])
    raw[0] ^= 0x01
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58check_decode(
            session, instance_id, tools.b58encode(bytes(raw))
        )


def test_base58check_decode_extra_leading_one(session: Session, instance_id: int):
    """A leading '1' is a leading zero byte, which breaks the checksum."""
    encoded = "1" + tools.b58check_encode(b"payload")
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.base58check_decode(session, instance_id, encoded)
