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

from trezorlib import btc, tools
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from . import testapp_ext
from .common import parametrize_using_common_fixtures
from .generated import messages as m
from .testapp_ext import TPUB_MAGIC, XPUB_MAGIC

# All hardened, so it works on Ed25519 too.
ACCOUNT_N = parse_path("m/44h/1h/0h")

# keys.json's tpub of ACCOUNT_N.
ACCOUNT_TPUB = "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U"


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


@pytest.mark.parametrize("compressed", [True, False])
def test_get_public_key_ed25519_matches_core(
    session: Session, instance_id: int, compressed: bool
):
    """`compressed` doesn't apply to Ed25519 keys."""
    node = btc.get_public_node(
        session, ACCOUNT_N, ecdsa_curve_name="ed25519", coin_name="Testnet"
    )
    public_key = testapp_ext.get_public_key(
        session, instance_id, ACCOUNT_N, compressed, m.Curve.CurveEd25519
    )
    # Core's node key has SLIP-10's 0x00 prefix.
    assert public_key == node.node.public_key[1:]


@pytest.mark.parametrize(
    "xpub_magic",
    [0x00000000, 0x0488B21E, 0x00174921, 0x8F1DAEB8, 0xFFFFFFFF],
    ids=["zero_110", "xpub_111", "florincoin_112", "particl_112", "max_112"],
)
def test_get_xpub_any_version(session: Session, instance_id: int, xpub_magic: int):
    """The version bytes set the xpub's length, from 110 to 112 characters."""
    node = tools.b58check_decode(ACCOUNT_TPUB)[4:]
    expected = tools.b58check_encode(xpub_magic.to_bytes(4, "big") + node)
    assert testapp_ext.get_xpub(session, instance_id, ACCOUNT_N, xpub_magic) == expected
