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

from trezorlib import cosi
from trezorlib.debuglink import DebugSession as Session

from . import testapp_ext
from .testapp_ext import INVALID_ENCODING, INVALID_SIGNATURE, SdkError, raises

PRIVKEYS = [bytes([i]) * 32 for i in range(1, 6)]
PUBKEYS = [cosi.pubkey_from_privkey(sk) for sk in PRIVKEYS]
MESSAGE = b"CoSi message"

# At most this many keys can be selected for a CoSi signature.
MAX_SELECTED = 3

# Not a point on the curve.
INVALID_POINT = bytes.fromhex(
    "0200000000000000000000000000000000000000000000000000000000000000"
)


def sign(message: bytes, mask: int, keys: list[bytes] = PRIVKEYS) -> bytes:
    selected = [sk for i, sk in enumerate(keys) if mask & (1 << i)]
    return cosi.sign_with_privkeys(message, selected, deterministic=True)


def verify(
    session: Session,
    instance_id: int,
    threshold: int,
    pubkeys: list[bytes],
    mask: int,
    signature: bytes,
    message: bytes = MESSAGE,
) -> None:
    testapp_ext.cosi_verify(
        session, instance_id, threshold, message, pubkeys, mask, signature
    )


# ============================================================================
# cosi_verify
# ============================================================================


@pytest.mark.parametrize(
    "threshold, n_keys, mask",
    [
        (1, 1, 0b1),
        (1, 3, 0b001),
        (1, 3, 0b100),
        (2, 3, 0b011),
        (2, 3, 0b101),
        (2, 3, 0b111),
        (3, 3, 0b111),
        (2, 5, 0b10100),
        (3, 5, 0b10101),
    ],
)
def test_cosi_verify(
    session: Session, instance_id: int, threshold: int, n_keys: int, mask: int
):
    signature = sign(MESSAGE, mask)
    # The reference implementation agrees.
    cosi.verify(signature, MESSAGE, threshold, PUBKEYS[:n_keys], mask)
    verify(session, instance_id, threshold, PUBKEYS[:n_keys], mask, signature)


@pytest.mark.parametrize("message", [b"", b"x" * 2000], ids=["empty", "long"])
def test_cosi_verify_message_lengths(
    session: Session, instance_id: int, message: bytes
):
    signature = sign(message, 0b11)
    verify(session, instance_id, 2, PUBKEYS[:2], 0b11, signature, message)


def test_cosi_verify_below_threshold(session: Session, instance_id: int):
    signature = sign(MESSAGE, 0b011)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 3, PUBKEYS[:3], 0b011, signature)


def test_cosi_verify_zero_threshold(session: Session, instance_id: int):
    signature = sign(MESSAGE, 0b1)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 0, PUBKEYS[:1], 0b1, signature)


def test_cosi_verify_empty_sigmask(session: Session, instance_id: int):
    signature = sign(MESSAGE, 0b1)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 1, PUBKEYS[:1], 0, signature)


def test_cosi_verify_too_many_selected(session: Session, instance_id: int):
    """More than MAX_SELECTED selected keys are refused, even if they signed."""
    mask = (1 << (MAX_SELECTED + 1)) - 1
    signature = sign(MESSAGE, mask)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 1, PUBKEYS[: MAX_SELECTED + 1], mask, signature)


def test_cosi_verify_sigmask_beyond_keys(session: Session, instance_id: int):
    """A sigmask bit with no public key behind it is refused."""
    signature = sign(MESSAGE, 0b011)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 1, PUBKEYS[:2], 0b111, signature)


def test_cosi_verify_wrong_signers(session: Session, instance_id: int):
    """The sigmask must name exactly the keys that signed."""
    signature = sign(MESSAGE, 0b011)
    for mask in (0b001, 0b101, 0b110, 0b111):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            verify(session, instance_id, 1, PUBKEYS[:3], mask, signature)


def test_cosi_verify_wrong_message(session: Session, instance_id: int):
    signature = sign(MESSAGE, 0b11)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 2, PUBKEYS[:2], 0b11, signature, MESSAGE + b"!")


def test_cosi_verify_tampered_signature(session: Session, instance_id: int):
    signature = sign(MESSAGE, 0b11)
    for i in (0, 32, 63):
        tampered = signature[:i] + bytes([signature[i] ^ 1]) + signature[i + 1 :]
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            verify(session, instance_id, 2, PUBKEYS[:2], 0b11, tampered)


def test_cosi_verify_invalid_point(session: Session, instance_id: int):
    signature = sign(MESSAGE, 0b11)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        verify(session, instance_id, 2, [PUBKEYS[0], INVALID_POINT], 0b11, signature)


@pytest.mark.parametrize("length", [0, 63, 65])
def test_cosi_verify_signature_length(session: Session, instance_id: int, length: int):
    signature = (sign(MESSAGE, 0b1) + b"\x00")[:length]
    with raises(SdkError.DataError, INVALID_ENCODING):
        verify(session, instance_id, 1, PUBKEYS[:1], 0b1, signature)


@pytest.mark.parametrize("length", [0, 31, 33])
def test_cosi_verify_public_key_length(session: Session, instance_id: int, length: int):
    signature = sign(MESSAGE, 0b1)
    key = (PUBKEYS[0] + b"\x00")[:length]
    with raises(SdkError.InvalidArgument):
        verify(session, instance_id, 1, [key], 0b1, signature)


@pytest.mark.parametrize("threshold, mask", [(256, 0b1), (1, 256)])
def test_cosi_verify_out_of_byte_range(
    session: Session, instance_id: int, threshold: int, mask: int
):
    """threshold and sigmask are single bytes."""
    with raises(SdkError.InvalidArgument):
        verify(session, instance_id, threshold, PUBKEYS[:1], mask, sign(MESSAGE, 0b1))


# ============================================================================
# cosi_combine_publickeys
# ============================================================================


@pytest.mark.parametrize("n_keys", [1, 2, 3, 5])
def test_cosi_combine_publickeys(session: Session, instance_id: int, n_keys: int):
    combined = testapp_ext.cosi_combine_publickeys(
        session, instance_id, PUBKEYS[:n_keys]
    )
    assert combined == cosi.combine_keys(PUBKEYS[:n_keys])


def test_cosi_combine_publickeys_single_key(session: Session, instance_id: int):
    """One key combines to itself."""
    assert (
        testapp_ext.cosi_combine_publickeys(session, instance_id, PUBKEYS[:1])
        == PUBKEYS[0]
    )


def test_cosi_combine_publickeys_order(session: Session, instance_id: int):
    """Combining is commutative."""
    a = testapp_ext.cosi_combine_publickeys(session, instance_id, PUBKEYS[:3])
    b = testapp_ext.cosi_combine_publickeys(session, instance_id, PUBKEYS[2::-1])
    assert a == b


def test_cosi_combine_publickeys_verifies(session: Session, instance_id: int):
    """A CoSi signature verifies as plain Ed25519 under the combined key."""
    combined = testapp_ext.cosi_combine_publickeys(session, instance_id, PUBKEYS[:2])
    signature = sign(MESSAGE, 0b11)
    cosi.verify_combined(signature, MESSAGE, combined)


def test_cosi_combine_publickeys_empty(session: Session, instance_id: int):
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.cosi_combine_publickeys(session, instance_id, [])


def test_cosi_combine_publickeys_invalid_point(session: Session, instance_id: int):
    for keys in ([PUBKEYS[0], INVALID_POINT], [INVALID_POINT, PUBKEYS[0]]):
        with raises(SdkError.DataError, INVALID_ENCODING):
            testapp_ext.cosi_combine_publickeys(session, instance_id, keys)


def test_cosi_combine_publickeys_single_invalid_point(
    session: Session, instance_id: int
):
    """A single key is returned as is, without checking that it is a point
    (trezor-crypto's `ed25519_cosi_combine_publickeys` copies it)."""
    assert (
        testapp_ext.cosi_combine_publickeys(session, instance_id, [INVALID_POINT])
        == INVALID_POINT
    )


@pytest.mark.parametrize("length", [0, 31, 33])
def test_cosi_combine_publickeys_key_length(
    session: Session, instance_id: int, length: int
):
    with raises(SdkError.InvalidArgument):
        testapp_ext.cosi_combine_publickeys(
            session, instance_id, [(PUBKEYS[0] + b"\x00")[:length]]
        )
