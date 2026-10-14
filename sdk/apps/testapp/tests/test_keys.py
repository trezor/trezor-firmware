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
from .testapp_ext import TPUB_MAGIC, UNEXPECTED_RESPONSE, XPUB_MAGIC, SdkError, raises

# SLIP-25 paths need an UnlockPath first, which an app can't do.
SLIP25_PATH = parse_path("m/10025h/1h/0h/1h")


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


def test_get_xpub_any_path(session: Session, instance_id: int):
    """Unlike signing, xpubs are not limited to the app's manifest paths."""
    address_n = parse_path("m/49h/0h/0h")
    node = btc.get_public_node(session, address_n, coin_name="Bitcoin")
    assert (
        testapp_ext.get_xpub(session, instance_id, address_n, XPUB_MAGIC) == node.xpub
    )


def test_get_xpub_slip25_forbidden(session: Session, instance_id: int):
    with raises(SdkError.DataError, UNEXPECTED_RESPONSE):
        testapp_ext.get_xpub(session, instance_id, SLIP25_PATH, TPUB_MAGIC)


@pytest.mark.parametrize("compressed", [True, False])
def test_get_public_key_slip25_forbidden(
    session: Session, instance_id: int, compressed: bool
):
    with raises(SdkError.DataError, UNEXPECTED_RESPONSE):
        testapp_ext.get_public_key(session, instance_id, SLIP25_PATH, compressed)


def test_app_still_works_after_failure(session: Session, instance_id: int):
    """A failed operation doesn't stop the app."""
    with raises(SdkError.DataError, UNEXPECTED_RESPONSE):
        testapp_ext.get_xpub(session, instance_id, SLIP25_PATH, TPUB_MAGIC)
    address_n = parse_path("m/44h/1h/0h")
    assert testapp_ext.get_xpub(session, instance_id, address_n, TPUB_MAGIC).startswith(
        "tpub"
    )
