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

import hashlib

import pytest

from trezorlib.debuglink import DebugSession as Session

from . import signing, testapp_ext
from .generated import messages as m
from .testapp_ext import INVALID_ENCODING, INVALID_SIGNATURE, SdkError, raises

ECDSA_CURVES = [
    pytest.param(m.EcdsaCurve.Secp256k1, id="secp256k1"),
    pytest.param(m.EcdsaCurve.Nist256p1, id="nist256p1"),
]
MESSAGES = [
    pytest.param(b"", id="empty"),
    pytest.param(b"hello", id="short"),
    pytest.param(bytes(range(256)) * 8, id="long"),
]
SECRETS = [1, 2, 0xC0FFEE, 2**255 - 19]


def ecdsa_case(curve: m.EcdsaCurve, message: bytes, secret: int = 0xC0FFEE):
    key = signing.ecdsa_key(curve, secret)
    digest = hashlib.sha256(message).digest()
    return key, digest, signing.ecdsa_sign(key, digest)


def flip(data: bytes, i: int) -> bytes:
    return data[:i] + bytes([data[i] ^ 0x01]) + data[i + 1 :]


# ============================================================================
# ECDSA: ecdsa_verify / ecdsa_verify_digest
# ============================================================================


@pytest.mark.parametrize("curve", ECDSA_CURVES)
@pytest.mark.parametrize("message", MESSAGES)
@pytest.mark.parametrize(
    "compressed", [True, False], ids=["compressed", "uncompressed"]
)
def test_ecdsa_verify(
    session: Session,
    instance_id: int,
    curve: m.EcdsaCurve,
    message: bytes,
    compressed: bool,
):
    key, _, rs = ecdsa_case(curve, message)
    pubkey = signing.public_key(key, compressed)
    testapp_ext.ecdsa_verify(session, instance_id, curve, pubkey, rs, message)


@pytest.mark.parametrize("curve", ECDSA_CURVES)
@pytest.mark.parametrize(
    "compressed", [True, False], ids=["compressed", "uncompressed"]
)
def test_ecdsa_verify_digest(
    session: Session, instance_id: int, curve: m.EcdsaCurve, compressed: bool
):
    for secret in SECRETS:
        key, digest, rs = ecdsa_case(curve, b"digest %d" % secret, secret)
        pubkey = signing.public_key(key, compressed)
        testapp_ext.ecdsa_verify_digest(session, instance_id, curve, pubkey, rs, digest)


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_verify_hashes_message(
    session: Session, instance_id: int, curve: m.EcdsaCurve
):
    """ecdsa_verify hashes the message itself: a signature over the
    message's digest verifies as the message, not as the digest."""
    key, digest, rs = ecdsa_case(curve, b"hash me")
    pubkey = signing.public_key(key, True)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        testapp_ext.ecdsa_verify(session, instance_id, curve, pubkey, rs, digest)


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_verify_wrong_key(
    session: Session, instance_id: int, curve: m.EcdsaCurve
):
    _, digest, rs = ecdsa_case(curve, b"message")
    other = signing.public_key(signing.ecdsa_key(curve, 0xBEEF), True)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        testapp_ext.ecdsa_verify_digest(session, instance_id, curve, other, rs, digest)


def test_ecdsa_verify_wrong_curve(session: Session, instance_id: int):
    """A secp256k1 signature doesn't verify as NIST P-256."""
    key, digest, rs = ecdsa_case(m.EcdsaCurve.Secp256k1, b"message")
    pubkey = signing.public_key(key, True)
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        testapp_ext.ecdsa_verify_digest(
            session, instance_id, m.EcdsaCurve.Nist256p1, pubkey, rs, digest
        )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_verify_tampered(session: Session, instance_id: int, curve: m.EcdsaCurve):
    key, digest, rs = ecdsa_case(curve, b"message")
    pubkey = signing.public_key(key, True)
    for i in (0, 31, 32, 63):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            testapp_ext.ecdsa_verify_digest(
                session, instance_id, curve, pubkey, flip(rs, i), digest
            )
    with raises(SdkError.DataError, INVALID_SIGNATURE):
        testapp_ext.ecdsa_verify_digest(
            session, instance_id, curve, pubkey, rs, flip(digest, 0)
        )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_verify_out_of_range(
    session: Session, instance_id: int, curve: m.EcdsaCurve
):
    """r and s outside [1, n-1] never verify."""
    key, digest, rs = ecdsa_case(curve, b"message")
    pubkey = signing.public_key(key, True)
    n = signing.CURVES[curve].order
    r, s = rs[:32], rs[32:]
    zero, order = b"\x00" * 32, n.to_bytes(32, "big")
    for bad in (zero + s, r + zero, order + s, r + order, b"\xff" * 64):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            testapp_ext.ecdsa_verify_digest(
                session, instance_id, curve, pubkey, bad, digest
            )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
@pytest.mark.parametrize("length", [0, 63, 65])
def test_ecdsa_verify_signature_length(
    session: Session, instance_id: int, curve: m.EcdsaCurve, length: int
):
    key, digest, rs = ecdsa_case(curve, b"message")
    pubkey = signing.public_key(key, True)
    signature = (rs + b"\x00")[:length]
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.ecdsa_verify_digest(
            session, instance_id, curve, pubkey, signature, digest
        )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
@pytest.mark.parametrize("length", [0, 31, 33])
def test_ecdsa_verify_digest_length(
    session: Session, instance_id: int, curve: m.EcdsaCurve, length: int
):
    key, digest, rs = ecdsa_case(curve, b"message")
    pubkey = signing.public_key(key, True)
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.ecdsa_verify_digest(
            session, instance_id, curve, pubkey, rs, (digest + b"\x00")[:length]
        )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_verify_public_key_format(
    session: Session, instance_id: int, curve: m.EcdsaCurve
):
    """Only 33- or 65-byte SEC1 keys are accepted."""
    key, digest, rs = ecdsa_case(curve, b"message")
    uncompressed = signing.public_key(key, False)
    compressed = signing.public_key(key, True)
    for bad in (
        b"",
        uncompressed[1:],  # raw 64-byte x || y
        compressed[:-1],
        uncompressed + b"\x00",
        bytes([compressed[0] ^ 1]) + compressed[1:],  # wrong y parity
    ):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            testapp_ext.ecdsa_verify_digest(
                session, instance_id, curve, bad, rs, digest
            )


# ============================================================================
# Ed25519: ed25519_verify
# ============================================================================


@pytest.mark.parametrize("message", MESSAGES)
def test_ed25519_verify(session: Session, instance_id: int, message: bytes):
    key = signing.ed25519_key(b"\x01" * 32)
    pubkey = signing.ed25519_public_key(key)
    testapp_ext.ed25519_verify(session, instance_id, pubkey, key.sign(message), message)


def test_ed25519_verify_invalid(session: Session, instance_id: int):
    key = signing.ed25519_key(b"\x01" * 32)
    pubkey = signing.ed25519_public_key(key)
    other = signing.ed25519_public_key(signing.ed25519_key(b"\x02" * 32))
    signature = key.sign(b"message")
    for pk, sig, msg in (
        (other, signature, b"message"),
        (pubkey, signature, b"messagf"),
        (pubkey, flip(signature, 0), b"message"),
        (pubkey, flip(signature, 63), b"message"),
    ):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            testapp_ext.ed25519_verify(session, instance_id, pk, sig, msg)


@pytest.mark.parametrize("length", [0, 31, 33])
def test_ed25519_verify_public_key_length(
    session: Session, instance_id: int, length: int
):
    key = signing.ed25519_key(b"\x01" * 32)
    pubkey = (signing.ed25519_public_key(key) + b"\x00")[:length]
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.ed25519_verify(session, instance_id, pubkey, key.sign(b"m"), b"m")


@pytest.mark.parametrize("length", [0, 63, 65])
def test_ed25519_verify_signature_length(
    session: Session, instance_id: int, length: int
):
    key = signing.ed25519_key(b"\x01" * 32)
    signature = (key.sign(b"m") + b"\x00")[:length]
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.ed25519_verify(
            session,
            instance_id,
            signing.ed25519_public_key(key),
            signature,
            b"m",
        )


# ============================================================================
# ecdsa_recover_pubkey
# ============================================================================


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_recover_pubkey(session: Session, instance_id: int, curve: m.EcdsaCurve):
    """Recovers the uncompressed key with the right recovery id, and some other
    key with the other one."""
    for secret in SECRETS:
        key, digest, rs = ecdsa_case(curve, b"recover %d" % secret, secret)
        pubkey = signing.public_key(key, False)
        recid = signing.recovery_id(curve, pubkey, rs, digest)
        result = testapp_ext.ecdsa_recover_pubkey(
            session, instance_id, curve, bytes([recid]) + rs, digest
        )
        assert result == pubkey
        other = testapp_ext.ecdsa_recover_pubkey(
            session, instance_id, curve, bytes([recid ^ 1]) + rs, digest
        )
        assert other != pubkey and len(other) == 65


@pytest.mark.parametrize("curve", ECDSA_CURVES)
@pytest.mark.parametrize("recid", [4, 27, 255])
def test_ecdsa_recover_pubkey_bad_recid(
    session: Session, instance_id: int, curve: m.EcdsaCurve, recid: int
):
    """Only recovery ids 0-3 are valid; a header byte (27+) is not."""
    _, digest, rs = ecdsa_case(curve, b"message")
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.ecdsa_recover_pubkey(
            session, instance_id, curve, bytes([recid]) + rs, digest
        )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_recover_pubkey_overflow_recid(
    session: Session, instance_id: int, curve: m.EcdsaCurve
):
    """Recovery ids 2 and 3 (r >= n - p) don't apply to an ordinary signature."""
    _, digest, rs = ecdsa_case(curve, b"message")
    for recid in (2, 3):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            testapp_ext.ecdsa_recover_pubkey(
                session, instance_id, curve, bytes([recid]) + rs, digest
            )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
def test_ecdsa_recover_pubkey_invalid_signature(
    session: Session, instance_id: int, curve: m.EcdsaCurve
):
    _, digest, _ = ecdsa_case(curve, b"message")
    n = signing.CURVES[curve].order
    for rs in (b"\x00" * 64, b"\x01" * 32 + b"\x00" * 32, n.to_bytes(32, "big") * 2):
        with raises(SdkError.DataError, INVALID_SIGNATURE):
            testapp_ext.ecdsa_recover_pubkey(
                session, instance_id, curve, b"\x00" + rs, digest
            )


@pytest.mark.parametrize("curve", ECDSA_CURVES)
@pytest.mark.parametrize(
    "signature_length, digest_length",
    [(0, 32), (64, 32), (66, 32), (65, 0), (65, 31), (65, 33)],
)
def test_ecdsa_recover_pubkey_lengths(
    session: Session,
    instance_id: int,
    curve: m.EcdsaCurve,
    signature_length: int,
    digest_length: int,
):
    """The signature is recid || r || s (65 bytes); the digest 32 bytes."""
    key, digest, rs = ecdsa_case(curve, b"message")
    recid = signing.recovery_id(curve, signing.public_key(key, False), rs, digest)
    signature = (bytes([recid]) + rs + b"\x00")[:signature_length]
    with raises(SdkError.DataError, INVALID_ENCODING):
        testapp_ext.ecdsa_recover_pubkey(
            session,
            instance_id,
            curve,
            signature,
            (digest + b"\x00")[:digest_length],
        )
