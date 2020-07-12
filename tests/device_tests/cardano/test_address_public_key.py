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

from trezorlib.cardano import get_address, get_public_key
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.skip_t1,
]


@pytest.mark.skip_ui
@parametrize_using_common_fixtures(
    ["cardano/get_address.json", "cardano/get_address.slip39.json"]
)
def test_cardano_get_address(client, parameters, result):
    address = get_address(client, parse_path(parameters["path"]))
    assert address == result["expected_address"]


@pytest.mark.skip_ui
@parametrize_using_common_fixtures(
    ["cardano/get_public_key.json", "cardano/get_public_key.slip39.json"]
)
def test_cardano_get_public_key(client, parameters, result):
    key = get_public_key(client, parse_path(parameters["path"]))

    assert key.node.public_key.hex() == result["public_key"]
    assert key.node.chain_code.hex() == result["chain_code"]
    assert key.xpub == result["public_key"] + result["chain_code"]
