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

"""Which keys an app gets: Core limits every function that takes a path to
the paths and curves in the app's manifest. The testapp allows
`m/44'/1'/account'/change/address_index/**` and `m/44'/1'/account'`, where
account is 0'-100', change 0-1 and address_index 0-1000000, on secp256k1,
nist256p1 and ed25519."""

import hashlib
from collections.abc import Callable
from functools import partial

import pytest

from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from . import testapp_ext
from .generated import messages as m
from .testapp_ext import DEFAULT_BIP32_PATH, TPUB_MAGIC, SdkError, assert_fails

DIGEST = hashlib.sha256(b"message").digest()
ADDRESS = "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"
SLIP44 = 1

ECDSA_CURVES = [
    (m.Curve.CurveSecp256k1, m.EcdsaCurve.Secp256k1),
    (m.Curve.CurveNist256p1, m.EcdsaCurve.Nist256p1),
]

# The edges of the manifest's ranges.
ALLOWED_PATHS = [
    pytest.param("m/44h/1h/100h", id="account_max"),
    pytest.param("m/44h/1h/100h/1/1000000", id="all_max"),
    pytest.param("m/44h/1h/0h/0/0/2147483647h", id="any_trailing"),
]

FORBIDDEN_PATHS = [
    pytest.param("m", id="root"),
    pytest.param("m/44h", id="purpose"),
    pytest.param("m/44h/1h", id="coin_type"),
    pytest.param("m/44h/1h/0h/0", id="no_address_index"),
    pytest.param("m/44h/0h/0h/0/0", id="other_coin"),
    pytest.param("m/44h/1h/0/0/0", id="unhardened_account"),
    pytest.param("m/44h/1h/101h/0/0", id="account_over_max"),
    pytest.param("m/44h/1h/0h/2/0", id="change_over_max"),
    pytest.param("m/44h/1h/0h/0h/0", id="hardened_change"),
    pytest.param("m/44h/1h/0h/0/1000001", id="address_index_over_max"),
    pytest.param("m/2147483647h", id="hardened_max"),
    # needs an UnlockPath, which an app can't send
    pytest.param("m/10025h/1h/0h/1h", id="slip25"),
]

# All hardened, so Ed25519 refuses them for the manifest, not for being
# unhardened.
FORBIDDEN_HARDENED_PATHS = [
    pytest.param("m", id="root"),
    pytest.param("m/44h", id="purpose"),
    pytest.param("m/44h/1h", id="coin_type"),
    pytest.param("m/44h/0h/0h", id="other_coin"),
    pytest.param("m/44h/1h/101h", id="account_over_max"),
    pytest.param("m/44h/1h/0h/0h", id="hardened_change"),
    pytest.param("m/10025h/1h/0h/1h", id="slip25"),
]


def ecdsa_calls(
    session: Session, instance_id: int, path: str
) -> dict[str, Callable[[], object]]:
    """Every function that takes a path, on the ECDSA curves."""
    address_n = parse_path(path)
    calls: dict[str, Callable[[], object]] = {}
    for curve, ecdsa_curve in ECDSA_CURVES:
        calls[f"get_xpub {curve.name}"] = partial(
            testapp_ext.get_xpub, session, instance_id, address_n, TPUB_MAGIC, curve
        )
        calls[f"get_public_key {curve.name}"] = partial(
            testapp_ext.get_public_key, session, instance_id, address_n, True, curve
        )
        calls[f"ecdsa_sign_digest {curve.name}"] = partial(
            testapp_ext.ecdsa_sign_digest,
            session,
            instance_id,
            address_n,
            DIGEST,
            True,
            curve=ecdsa_curve,
        )
    calls["ecdsa_sign_digest Ethereum"] = partial(
        testapp_ext.ecdsa_sign_digest,
        session,
        instance_id,
        address_n,
        DIGEST,
        False,
        m.CanonicalSig.Ethereum,
    )
    calls["get_address_mac"] = partial(
        testapp_ext.get_address_mac, session, instance_id, address_n, ADDRESS, SLIP44
    )
    return calls


def ed25519_calls(
    session: Session, instance_id: int, path: str
) -> dict[str, Callable[[], object]]:
    """Every function that takes a path, on Ed25519."""
    address_n = parse_path(path)
    return {
        "get_public_key": partial(
            testapp_ext.get_public_key,
            session,
            instance_id,
            address_n,
            False,
            m.Curve.CurveEd25519,
        ),
        "ed25519_sign": partial(
            testapp_ext.ed25519_sign, session, instance_id, address_n, b"message"
        ),
    }


def succeeds(what: str, call: Callable[[], object]) -> None:
    try:
        call()
    except Exception as e:
        pytest.fail(f"{what} failed: {e}")


@pytest.mark.parametrize("path", ALLOWED_PATHS)
def test_allowed_path(session: Session, instance_id: int, path: str):
    for what, call in ecdsa_calls(session, instance_id, path).items():
        succeeds(what, call)


def test_allowed_path_ed25519(session: Session, instance_id: int):
    for what, call in ed25519_calls(session, instance_id, "m/44h/1h/100h").items():
        succeeds(what, call)


@pytest.mark.parametrize("path", FORBIDDEN_PATHS)
def test_forbidden_path(session: Session, instance_id: int, path: str):
    for what, call in ecdsa_calls(session, instance_id, path).items():
        assert_fails(what, call, SdkError.ServiceError)


@pytest.mark.parametrize("path", FORBIDDEN_HARDENED_PATHS)
def test_forbidden_path_ed25519(session: Session, instance_id: int, path: str):
    calls = ed25519_calls(session, instance_id, path)
    calls["get_xpub"] = partial(
        testapp_ext.get_xpub,
        session,
        instance_id,
        parse_path(path),
        TPUB_MAGIC,
        m.Curve.CurveEd25519,
    )
    for what, call in calls.items():
        assert_fails(what, call, SdkError.ServiceError)


def test_ed25519_unhardened(session: Session, instance_id: int):
    """Ed25519 keys only exist on hardened paths, even inside the manifest."""
    for what, call in ed25519_calls(session, instance_id, DEFAULT_BIP32_PATH).items():
        assert_fails(what, call, SdkError.ServiceError)


def test_curve_not_allowed(session: Session, instance_id: int):
    """Curve25519 isn't in the app's manifest."""
    address_n = parse_path("m/44h/1h/0h")
    curve = m.Curve.CurveCurve25519
    assert_fails(
        "get_public_key",
        partial(
            testapp_ext.get_public_key, session, instance_id, address_n, False, curve
        ),
        SdkError.ServiceError,
    )
    assert_fails(
        "get_xpub",
        partial(
            testapp_ext.get_xpub, session, instance_id, address_n, TPUB_MAGIC, curve
        ),
        SdkError.ServiceError,
    )
