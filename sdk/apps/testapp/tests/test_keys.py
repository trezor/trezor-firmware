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

from trezorlib import btc, messages, tools
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from . import signing, testapp_ext
from .common import parametrize_using_common_fixtures
from .generated import messages as m
from .testapp_ext import INVALID_PUBLIC_KEY, TPUB_MAGIC, XPUB_MAGIC, SdkError, raises

# All hardened, so it works on Ed25519 too.
ACCOUNT_N = parse_path("m/44h/1h/0h")

# keys.json's tpub of ACCOUNT_N.
ACCOUNT_TPUB = "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U"


def assert_node_matches(node: m.PublicNode, core: messages.HDNodeType) -> None:
    assert node.depth == core.depth
    assert node.fingerprint == core.fingerprint
    assert node.child_num == core.child_num
    assert node.chain_code == core.chain_code
    assert node.public_key == core.public_key


# ============================================================================
# get_public_node
# ============================================================================


@parametrize_using_common_fixtures("keys.json")
def test_get_public_node(session: Session, instance_id: int, parameters, result):
    address_n = parse_path(parameters["path"])
    node = testapp_ext.get_public_node(session, instance_id, address_n)
    assert node.public_key.hex() == result["public_key_compressed"]
    assert node.xpub is None
    assert (
        testapp_ext.get_xpub(session, instance_id, address_n, TPUB_MAGIC)
        == result["tpub"]
    )
    assert (
        testapp_ext.get_xpub(session, instance_id, address_n, XPUB_MAGIC)
        == result["xpub"]
    )


def test_get_public_node_matches_core(session: Session, instance_id: int):
    """The app gets the same node Core's own GetPublicKey returns."""
    core = btc.get_public_node(session, ACCOUNT_N, coin_name="Testnet")
    node = testapp_ext.get_public_node(
        session, instance_id, ACCOUNT_N, xpub_magic=TPUB_MAGIC
    )
    assert_node_matches(node, core.node)
    assert node.xpub == core.xpub


@pytest.mark.parametrize(
    "curve, curve_name",
    [
        (m.Curve.CurveSecp256k1, "secp256k1"),
        (m.Curve.CurveNist256p1, "nist256p1"),
        (m.Curve.CurveEd25519, "ed25519"),
    ],
)
def test_get_public_node_curve_matches_core(
    session: Session, instance_id: int, curve: m.Curve, curve_name: str
):
    """Ed25519 keys keep SLIP-10's 0x00 prefix, like Core's."""
    core = btc.get_public_node(
        session, ACCOUNT_N, ecdsa_curve_name=curve_name, coin_name="Testnet"
    )
    node = testapp_ext.get_public_node(session, instance_id, ACCOUNT_N, curve)
    assert_node_matches(node, core.node)


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


# ============================================================================
# ecdsa_uncompress_pubkey
# ============================================================================


@parametrize_using_common_fixtures("keys.json")
def test_ecdsa_uncompress_pubkey(
    session: Session, instance_id: int, parameters, result
):
    address_n = parse_path(parameters["path"])
    node = testapp_ext.get_public_node(session, instance_id, address_n)
    uncompressed = testapp_ext.ecdsa_uncompress_pubkey(
        session, instance_id, node.public_key
    )
    assert uncompressed.hex() == result["public_key_uncompressed"]


@pytest.mark.parametrize(
    "curve",
    [
        pytest.param(m.EcdsaCurve.Secp256k1, id="secp256k1"),
        pytest.param(m.EcdsaCurve.Nist256p1, id="nist256p1"),
    ],
)
@pytest.mark.parametrize("secret", [1, 2, 0xC0FFEE])
def test_ecdsa_uncompress_pubkey_curves(
    session: Session, instance_id: int, curve: m.EcdsaCurve, secret: int
):
    """Both y parities (0x02 and 0x03) on both curves."""
    key = signing.ecdsa_key(curve, secret)
    compressed = signing.public_key(key, True)
    uncompressed = signing.public_key(key, False)
    assert (
        testapp_ext.ecdsa_uncompress_pubkey(session, instance_id, compressed, curve)
        == uncompressed
    )


@pytest.mark.parametrize(
    "public_key",
    [
        # x = 5 is not on secp256k1
        pytest.param(b"\x02" + (5).to_bytes(32, "big"), id="not_on_curve"),
        pytest.param(b"\x04" + bytes(32), id="uncompressed_prefix"),
        pytest.param(b"\x00" + bytes(32), id="zero_prefix"),
    ],
)
def test_ecdsa_uncompress_pubkey_invalid(
    session: Session, instance_id: int, public_key: bytes
):
    with raises(SdkError.DataError, INVALID_PUBLIC_KEY):
        testapp_ext.ecdsa_uncompress_pubkey(session, instance_id, public_key)


@pytest.mark.parametrize("length", [0, 32, 34, 65])
def test_ecdsa_uncompress_pubkey_wrong_length(
    session: Session, instance_id: int, length: int
):
    """Refused by the app before the call: the SDK takes exactly 33 bytes."""
    with raises(SdkError.InvalidArgument):
        testapp_ext.ecdsa_uncompress_pubkey(session, instance_id, b"\x02" * length)
