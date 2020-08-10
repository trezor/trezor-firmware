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

from trezorlib.cardano import get_public_key
from trezorlib.tools import parse_path


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path,public_key,chain_code",
    [
        (
            "m/44'/1815'/0'",
            "c0fce1839f1a84c4e770293ac2f5e0875141b29017b7f56ab135352d00ad6966",
            "07faa161c9f5464315d2855f70fdf1431d5fa39eb838767bf17b69772137452f",
        ),
        (
            "m/44'/1815'/1'",
            "ea5dde31b9f551e08a5b6b2f98b8c42c726f726c9ce0a7072102ead53bd8f21e",
            "70f131bb799fd659c997221ad8cae7dcce4e8da701f8101cf15307fd3a3712a1",
        ),
        (
            "m/1852'/1815'/0'",
            "d507c8f866691bd96e131334c355188b1a1d0b2fa0ab11545075aab332d77d9e",
            "b19657ad13ee581b56b0f8d744d66ca356b93d42fe176b3de007d53e9c4c4e7a",
        ),
        (
            "m/1852'/1815'/1'",
            "140791584001446365f169c82241c7c214475000180dab39fa0588fc9c3d6d80",
            "7f9f812d49816844b52e319857aa75961724ad1a146701679d02d7168622233d",
        ),
        (
            "m/1852'/1815'/2'",
            "ff6ccc3097ca79fc29fe92a9639c47644746780c63acae10a9e6f03bf5c919dd",
            "27d985feabf40d83a30aa4645ff008c068187559dd224ba59e26d0d2dc3598ce",
        ),
        (
            "m/1852'/1815'/3'",
            "be81ace1f63f4f0cae74dd274a72d7818f238bc764ab3e0dc0beb1945b756dca",
            "29034f036a162ac4f9f9f397b2d1f289754bb6633915f26b199e156f81d05c88",
        ),
    ],
)
def test_cardano_get_public_key(client, path, public_key, chain_code):
    key = get_public_key(client, parse_path(path))

    assert key.node.public_key.hex() == public_key
    assert key.node.chain_code.hex() == chain_code
    assert key.xpub == public_key + chain_code
