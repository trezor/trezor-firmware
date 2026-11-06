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

from trezorlib import btc
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from . import testapp_ext
from .common import parametrize_using_common_fixtures
from .generated import messages as m
from .testapp_ext import (
    DEFAULT_BIP32_PATH,
    TPUB_MAGIC,
    XPUB_MAGIC,
    SdkError,
    raises,
)

# SLIP-25 paths need an UnlockPath first, which an app can't do.
SLIP25_PATH = parse_path("m/10025h/1h/0h/1h")

# All hardened, so it works on Ed25519 too.
ACCOUNT_N = parse_path("m/44h/1h/0h")

# Paths outside the app's manifest.
FORBIDDEN_PATHS = [
    pytest.param("m", id="root"),
    pytest.param("m/44h", id="purpose"),
    pytest.param("m/44h/1h/0h/0/2147483647", id="unhardened_max"),
    pytest.param("m/2147483647h", id="hardened_max"),
    pytest.param("m/44h/0h/0h/0/0", id="other_coin"),
]


@parametrize_using_common_fixtures("keys.json")
def test_get_xpub(session: Session, instance_id: int, parameters, result):
    address_n = parse_path(parameters["path"])
    assert (
        testapp_ext.get_xpub(session, instance_id, address_n, TPUB_MAGIC)
        == result["tpub"]
    )
    assert (
        testapp_ext.get_xpub(session, instance_id, address_n, XPUB_MAGIC)
        == result["xpub"]
    )


@parametrize_using_common_fixtures("keys.json")
def test_get_public_key(session: Session, instance_id: int, parameters, result):
    address_n = parse_path(parameters["path"])
    compressed = testapp_ext.get_public_key(session, instance_id, address_n, True)
    uncompressed = testapp_ext.get_public_key(session, instance_id, address_n, False)
    assert compressed.hex() == result["public_key_compressed"]
    assert uncompressed.hex() == result["public_key_uncompressed"]


def test_get_xpub_matches_core(session: Session, instance_id: int):
    """The app gets the same xpub Core's own GetPublicKey returns."""
    address_n = parse_path("m/44h/1h/0h")
    node = btc.get_public_node(session, address_n, coin_name="Testnet")
    assert (
        testapp_ext.get_xpub(session, instance_id, address_n, TPUB_MAGIC) == node.xpub
    )
    assert (
        testapp_ext.get_public_key(session, instance_id, address_n, True)
        == node.node.public_key
    )


@pytest.mark.parametrize("path", FORBIDDEN_PATHS)
def test_get_xpub_forbidden_path(session: Session, instance_id: int, path: str):
    """Like signing, keys are limited to the app's manifest paths."""
    with raises(SdkError.ServiceError):
        testapp_ext.get_xpub(session, instance_id, parse_path(path), XPUB_MAGIC)


@pytest.mark.parametrize("path", FORBIDDEN_PATHS)
def test_get_public_key_forbidden_path(session: Session, instance_id: int, path: str):
    with raises(SdkError.ServiceError):
        testapp_ext.get_public_key(session, instance_id, parse_path(path), True)


@pytest.mark.parametrize(
    "curve, curve_name",
    [
        (m.Curve.CurveSecp256k1, "secp256k1"),
        (m.Curve.CurveNist256p1, "nist256p1"),
    ],
)
def test_get_xpub_curve_matches_core(
    session: Session, instance_id: int, curve: m.Curve, curve_name: str
):
    node = btc.get_public_node(
        session, ACCOUNT_N, ecdsa_curve_name=curve_name, coin_name="Testnet"
    )
    assert (
        testapp_ext.get_xpub(session, instance_id, ACCOUNT_N, TPUB_MAGIC, curve)
        == node.xpub
    )
    assert (
        testapp_ext.get_public_key(session, instance_id, ACCOUNT_N, True, curve)
        == node.node.public_key
    )


def test_get_public_key_ed25519_matches_core(session: Session, instance_id: int):
    node = btc.get_public_node(
        session, ACCOUNT_N, ecdsa_curve_name="ed25519", coin_name="Testnet"
    )
    public_key = testapp_ext.get_public_key(
        session, instance_id, ACCOUNT_N, False, m.Curve.CurveEd25519
    )
    # Core's node key has SLIP-10's 0x00 prefix.
    assert public_key == node.node.public_key[1:]


def test_get_public_key_ed25519_unhardened(session: Session, instance_id: int):
    with raises(SdkError.ServiceError):
        testapp_ext.get_public_key(
            session,
            instance_id,
            parse_path(DEFAULT_BIP32_PATH),
            False,
            m.Curve.CurveEd25519,
        )


def test_curve_not_allowed(session: Session, instance_id: int):
    """Curve25519 isn't in the app's manifest."""
    with raises(SdkError.ServiceError):
        testapp_ext.get_public_key(
            session, instance_id, ACCOUNT_N, False, m.Curve.CurveCurve25519
        )
    with raises(SdkError.ServiceError):
        testapp_ext.get_xpub(
            session, instance_id, ACCOUNT_N, TPUB_MAGIC, m.Curve.CurveCurve25519
        )


def test_get_xpub_slip25_forbidden(session: Session, instance_id: int):
    with raises(SdkError.ServiceError):
        testapp_ext.get_xpub(session, instance_id, SLIP25_PATH, TPUB_MAGIC)


@pytest.mark.parametrize("compressed", [True, False])
def test_get_public_key_slip25_forbidden(
    session: Session, instance_id: int, compressed: bool
):
    with raises(SdkError.ServiceError):
        testapp_ext.get_public_key(session, instance_id, SLIP25_PATH, compressed)


def test_app_still_works_after_failure(session: Session, instance_id: int):
    """A failed operation doesn't stop the app."""
    with raises(SdkError.ServiceError):
        testapp_ext.get_xpub(session, instance_id, SLIP25_PATH, TPUB_MAGIC)
    address_n = parse_path("m/44h/1h/0h")
    assert testapp_ext.get_xpub(session, instance_id, address_n, TPUB_MAGIC).startswith(
        "tpub"
    )
