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
from trezorlib.tools import parse_path

from . import signing, testapp_ext
from .generated import messages as m
from .testapp_ext import DEFAULT_BIP32_PATH, OPERATION_FAILED, SdkError, raises

ADDRESS_N = parse_path(DEFAULT_BIP32_PATH)

DIGESTS = [
    pytest.param(hashlib.sha256(b"message").digest(), id="sha256"),
    pytest.param(b"\xff" * 32, id="ones"),
    pytest.param(bytes(range(32)), id="pattern"),
]

# Paths outside the app's manifest (m/44'/1'/account'/change/address_index/**).
FORBIDDEN_PATHS = [
    pytest.param("m/44h/0h/0h/0/0", id="other_coin"),
    pytest.param("m/44h/1h/0h", id="account_level"),
    pytest.param("m/44h/1h/0/0/0", id="unhardened_account"),
    pytest.param("m", id="root"),
]


def public_key(session: Session, instance_id: int) -> bytes:
    return testapp_ext.get_public_key(session, instance_id, ADDRESS_N, False)


def check_signature(
    signature: bytes, pubkey: bytes, digest: bytes, header_base: int
) -> int:
    """Checks a 65-byte header || r || s signature; returns its recovery id."""
    assert len(signature) == 65
    rs = signature[1:]
    assert signing.ecdsa_verify(pubkey, m.EcdsaCurve.Secp256k1, rs, digest)
    recid = signing.recovery_id(m.EcdsaCurve.Secp256k1, pubkey, rs, digest)
    assert signature[0] == header_base + recid
    return recid


# ============================================================================
# ecdsa_sign_digest
# ============================================================================


@pytest.mark.parametrize("digest", DIGESTS)
@pytest.mark.parametrize("compressed", [True, False])
def test_ecdsa_sign_digest(
    session: Session, instance_id: int, digest: bytes, compressed: bool
):
    signature = testapp_ext.ecdsa_sign_digest(
        session, instance_id, ADDRESS_N, digest, compressed
    )
    # Bitcoin-style header: 27 + recovery id, + 4 for a compressed key.
    check_signature(
        signature, public_key(session, instance_id), digest, 31 if compressed else 27
    )


def test_ecdsa_sign_digest_deterministic(session: Session, instance_id: int):
    digest = hashlib.sha256(b"deterministic").digest()
    a = testapp_ext.ecdsa_sign_digest(session, instance_id, ADDRESS_N, digest, True)
    b = testapp_ext.ecdsa_sign_digest(session, instance_id, ADDRESS_N, digest, True)
    assert a == b


def test_ecdsa_sign_digest_recovers(session: Session, instance_id: int):
    """The signature's recovery id recovers the signing key through the app."""
    digest = hashlib.sha256(b"recover me").digest()
    signature = testapp_ext.ecdsa_sign_digest(
        session, instance_id, ADDRESS_N, digest, False
    )
    recid = signature[0] - 27
    recovered = testapp_ext.ecdsa_recover_pubkey(
        session,
        instance_id,
        m.EcdsaCurve.Secp256k1,
        bytes([recid]) + signature[1:],
        digest,
    )
    assert recovered == public_key(session, instance_id)


def test_ecdsa_sign_digest_other_address(session: Session, instance_id: int):
    """Another manifest path signs with another key."""
    digest = hashlib.sha256(b"message").digest()
    other = parse_path("m/44h/1h/1h/1/7")
    signature = testapp_ext.ecdsa_sign_digest(
        session, instance_id, other, digest, False
    )
    pubkey = testapp_ext.get_public_key(session, instance_id, other, False)
    check_signature(signature, pubkey, digest, 27)
    assert pubkey != public_key(session, instance_id)


@pytest.mark.parametrize("compressed", [True, False])
def test_ecdsa_sign_digest_zero_digest(
    session: Session, instance_id: int, compressed: bool
):
    """An all-zero digest is refused: its signature could be forged for any key."""
    with raises(SdkError.DataError, OPERATION_FAILED):
        testapp_ext.ecdsa_sign_digest(
            session, instance_id, ADDRESS_N, b"\x00" * 32, compressed
        )


@pytest.mark.parametrize("length", [0, 31, 33, 64])
def test_ecdsa_sign_digest_wrong_length(
    session: Session, instance_id: int, length: int
):
    with raises(SdkError.InvalidArgument):
        testapp_ext.ecdsa_sign_digest(
            session, instance_id, ADDRESS_N, b"\x01" * length, True
        )


def test_ed25519_sign_wrong_curve(session: Session, instance_id: int):
    """The testapp's curve is secp256k1, so Core refuses Ed25519 signing."""
    with raises(SdkError.DataError, OPERATION_FAILED):
        testapp_ext.ed25519_sign(session, instance_id, ADDRESS_N, b"message")


@pytest.mark.parametrize("path", FORBIDDEN_PATHS)
def test_ecdsa_sign_digest_forbidden_path(
    session: Session, instance_id: int, path: str
):
    with raises(SdkError.DataError, OPERATION_FAILED):
        testapp_ext.ecdsa_sign_digest(
            session, instance_id, parse_path(path), b"\x01" * 32, True
        )


# ============================================================================
# ecdsa_sign_digest with an Ethereum-canonical signature
# ============================================================================


@pytest.mark.parametrize("digest", DIGESTS)
def test_ecdsa_sign_digest_canonical_ethereum(
    session: Session, instance_id: int, digest: bytes
):
    signature = testapp_ext.ecdsa_sign_digest(
        session, instance_id, ADDRESS_N, digest, False, m.CanonicalSig.Ethereum
    )
    # Ethereum-style: v = 27 + recovery id, which fits in one bit.
    recid = check_signature(signature, public_key(session, instance_id), digest, 27)
    assert recid in (0, 1)


def test_ecdsa_sign_digest_canonical_ethereum_zero_digest(
    session: Session, instance_id: int
):
    """An all-zero digest is refused: its signature could be forged for any key."""
    with raises(SdkError.DataError, OPERATION_FAILED):
        testapp_ext.ecdsa_sign_digest(
            session,
            instance_id,
            ADDRESS_N,
            b"\x00" * 32,
            False,
            m.CanonicalSig.Ethereum,
        )


@pytest.mark.parametrize("path", FORBIDDEN_PATHS)
def test_ecdsa_sign_digest_canonical_ethereum_forbidden_path(
    session: Session, instance_id: int, path: str
):
    with raises(SdkError.DataError, OPERATION_FAILED):
        testapp_ext.ecdsa_sign_digest(
            session,
            instance_id,
            parse_path(path),
            b"\x01" * 32,
            False,
            m.CanonicalSig.Ethereum,
        )
