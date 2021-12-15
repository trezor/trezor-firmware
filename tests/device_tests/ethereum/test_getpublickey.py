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

from trezorlib import ethereum
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


@parametrize_using_common_fixtures("ethereum/getpublickey.json")
def test_ethereum_getpublickey(client, parameters, result):
    path = parse_path(parameters["path"])
    res = ethereum.get_public_node(client, path)
    assert res.node.depth == len(path)
    assert res.node.fingerprint == result["fingerprint"]
    assert res.node.child_num == result["child_num"]
    assert res.node.chain_code.hex() == result["chain_code"]
    assert res.node.public_key.hex() == result["public_key"]
    assert res.xpub == result["xpub"]
