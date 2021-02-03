# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

PATH_PRIVATE = parse_path("m/17h/0h/1h/2h/3h")
PATH_PUBLIC = parse_path("m/17h/0h/1h/2h/3h/42")

VECTORS = (  # curve, path, pubkey
    (
        "secp256k1",
        PATH_PRIVATE,
        "02f65ce170451f66f46daf9486b0cf266bd199a3e67f734e469556745a78d254ee",
    ),
    (
        "secp256k1",
        PATH_PUBLIC,
        "0212f4629f4f224db0f778ca68abd1c53e21dd02e76dbd1f7312788544b5b1e042",
    ),
    (
        "nist256p1",
        PATH_PRIVATE,
        "0324c6860c25cdf7a8c103666662ac6183bf5a181a3341ea4130dcc6fdee7919e4",
    ),
    (
        "nist256p1",
        PATH_PUBLIC,
        "03b93f7e6c777143ad4eeb590aaa7cdcd95980cf68d3f75dc2c31ca637ec50c49b",
    ),
    (
        "ed25519",
        PATH_PRIVATE,
        "002e28dc0346d6d30d4e33f53c47f2fa97f3cfb5e80fc30fa3570fccf30652718a",
    ),
)


@pytest.mark.parametrize("curve, path, pubkey", VECTORS)
def test_publickey_curve(client, curve, path, pubkey):
    resp = btc.get_public_node(client, path, ecdsa_curve_name=curve)
    assert resp.node.public_key.hex() == pubkey


def test_ed25519_public(client):
    with pytest.raises(TrezorFailure):
        btc.get_public_node(client, PATH_PUBLIC, ecdsa_curve_name="ed25519")


@pytest.mark.xfail(reason="Currently path validation on get_public_node is disabled.")
def test_coin_and_curve(client):
    with pytest.raises(
        TrezorFailure, match="Cannot use coin_name or script_type with ecdsa_curve_name"
    ):
        btc.get_public_node(
            client, PATH_PRIVATE, coin_name="Bitcoin", ecdsa_curve_name="ed25519"
        )
